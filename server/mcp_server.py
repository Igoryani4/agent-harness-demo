import json
import os
import subprocess
import time
from pathlib import Path

from fastmcp import FastMCP

# 1. Инициализация сервера
mcp = FastMCP("bss-harness-tools")

# 2. Настройки путей и трассировки
TRACE_FILE = Path(os.getenv("TRACE_FILE", "traces/tool_calls.jsonl"))
# Все операции с файлами должны быть строго внутри этой директории
WORKSPACE_ROOT = Path(os.getenv("WORKSPACE_ROOT", "./workspace")).resolve()


def _safe_path(relative_path: str) -> Path:
    """Защита от path traversal: запрещает выходить за пределы workspace."""
    target = (WORKSPACE_ROOT / relative_path).resolve()
    if not str(target).startswith(str(WORKSPACE_ROOT)):
        raise ValueError("Access denied: path escapes workspace")
    return target


def _log_tool_call(tool: str, args: dict, result_preview: str, ok: bool, duration_ms: int):
    """Пишет JSONL-трейс для observability и последующих evals."""
    TRACE_FILE.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "ts": time.time(),
        "tool": tool,
        "args": args,
        "ok": ok,
        "duration_ms": duration_ms,
        "result_preview": result_preview[:300],
    }
    with TRACE_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


# ============================================================
# TOOL 1: read_file (с защитой от path traversal и лимитом размера)
# ============================================================
@mcp.tool
def read_file(path: str, max_bytes: int = 50_000) -> str:
    """Read a text file inside the workspace (read-only, path-guarded)."""
    t0 = time.time()
    try:
        target = _safe_path(path)
        content = target.read_text(errors="replace")[:max_bytes]
        _log_tool_call("read_file", {"path": path}, content, True, int((time.time() - t0) * 1000))
        return content
    except Exception as e:
        _log_tool_call("read_file", {"path": path}, str(e), False, int((time.time() - t0) * 1000))
        return f"ERROR: {e}"


# ============================================================
# TOOL 2: git_diff (только чтение)
# ============================================================
@mcp.tool
def git_diff(staged: bool = False) -> str:
    """Return git diff for the workspace (read-only, repo-guarded)."""
    t0 = time.time()
    try:
        # Проверяем, что workspace — это корень git-репозитория
        toplevel = subprocess.run(
            ["git", "-C", str(WORKSPACE_ROOT), "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, timeout=5,
        )
        if toplevel.returncode != 0:
            raise RuntimeError("workspace is not a git repository")
        repo_root = Path(toplevel.stdout.strip()).resolve()
        if repo_root != WORKSPACE_ROOT:
            raise RuntimeError(
                f"workspace is not the repo root (found {repo_root}). "
                f"Refusing to diff parent repository."
            )

        cmd = ["git", "-C", str(WORKSPACE_ROOT), "diff", "--", "."]
        if staged:
            cmd.append("--cached")

        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        output = proc.stdout or proc.stderr
        _log_tool_call("git_diff", {"staged": staged}, output, proc.returncode == 0,
                       int((time.time() - t0) * 1000))
        return output
    except Exception as e:
        _log_tool_call("git_diff", {"staged": staged}, str(e), False,
                       int((time.time() - t0) * 1000))
        return f"ERROR: {e}"

@mcp.tool
def search_codebase(pattern: str, path: str = ".", max_results: int = 30) -> list[dict]:
    """Grep text in workspace files (read-only, hidden files skipped)."""
    t0 = time.time()
    try:
        target = _safe_path(path)
        results = []
        for f in target.rglob("*"):
            if not f.is_file() or f.stat().st_size > 1_000_000:
                continue
            rel = f.relative_to(WORKSPACE_ROOT)
            if any(part.startswith(".") for part in rel.parts):
                continue
            try:
                for i, line in enumerate(f.read_text(errors="replace").splitlines(), 1):
                    if pattern in line:
                        results.append({"file": str(rel), "line": i, "text": line[:200]})
                        if len(results) >= max_results:
                            break
            except Exception:
                continue
            if len(results) >= max_results:
                break
        _log_tool_call("search_codebase", {"pattern": pattern, "path": path},
                       f"{len(results)} matches", True, int((time.time() - t0) * 1000))
        return results
    except Exception as e:
        _log_tool_call("search_codebase", {"pattern": pattern, "path": path},
                       str(e), False, int((time.time() - t0) * 1000))
        return [{"error": str(e)}]

# ============================================================
# TOOL 3: run_tests (запуск в изолированном Docker-песочнице)
# ============================================================
@mcp.tool
def run_tests(test_path: str = "tests", timeout_sec: int = 120) -> dict:
    """
    Auto-detect: if workspace/java/pom.xml exists → run Java in harness-java-sandbox;
    else → run Python pytest in harness-sandbox.
    """
    t0 = time.time()
    java_pom = WORKSPACE_ROOT / "java" / "pom.xml"

    if java_pom.exists():
        cmd = [
            "docker", "run", "--rm",
            "--network=none", "--read-only",
            "--tmpfs", "/tmp:rw,exec,size=512m",
            "-v", f"{WORKSPACE_ROOT}:/workspace:ro",
            "harness-java-sandbox:latest",
            "java",
        ]
    else:
        cmd = [
            "docker", "run", "--rm",
            "--network=none", "--read-only",
            "--tmpfs", "/tmp:size=64m",
            "--memory=512m", "--cpus=1",
            "-v", f"{WORKSPACE_ROOT}:/workspace:ro",
            "harness-sandbox:latest",
            "python", "-m", "pytest", test_path, "-q", "--maxfail=1",
        ]

    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout_sec)
        output = (proc.stdout + proc.stderr)[-6000:]
        passed = proc.returncode == 0
        result = {"passed": passed, "failed": 0 if passed else 1, "output": output}
    except subprocess.TimeoutExpired:
        result = {"passed": False, "failed": -1, "output": "TIMEOUT"}
    except Exception as e:
        result = {"passed": False, "failed": -1, "output": f"ERROR: {e}"}

    _log_tool_call("run_tests", {"test_path": test_path}, str(result), result["passed"],
                   int((time.time() - t0) * 1000))
    return result


if __name__ == "__main__":
    # Транспорт SSE удобен для подключения оркестратора по HTTP
    mcp.run(transport="sse", host="0.0.0.0", port=8000)