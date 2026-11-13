import subprocess
from pathlib import Path

from orchestrator.state import HarnessState


WORKSPACE = Path("workspace").resolve()
STATE_DIR = Path("state").resolve()


async def applier_node(state: HarnessState) -> dict:
    """Применяет diff через git apply. Вызывается только после approve."""
    if state.get("review_decision") != "approve":
        return {"apply_ok": False, "apply_error": "not approved"}

    diff = state["diff"]

    if not diff.strip():
        return {"apply_ok": False, "apply_error": "empty diff"}

    # Защита от no-op: - и + строки идентичны
    minus = [l[1:].strip() for l in diff.splitlines()
             if l.startswith("-") and not l.startswith("---")]
    plus = [l[1:].strip() for l in diff.splitlines()
            if l.startswith("+") and not l.startswith("+++")]
    if minus and plus and minus == plus:
        return {"apply_ok": False, "apply_error": "no-op diff: minus == plus"}

    # Только теперь пишем патч и пробуем применить
    diff_path = STATE_DIR / "pending.patch"
    diff_path.parent.mkdir(parents=True, exist_ok=True)
    diff_path.write_text(diff, encoding="utf-8")

    check = subprocess.run(
        ["git", "-C", str(WORKSPACE), "apply", "--check", str(diff_path)],
        capture_output=True, text=True,
    )
    if check.returncode != 0:
        return {"apply_ok": False, "apply_error": check.stderr[-2000:]}

    apply = subprocess.run(
        ["git", "-C", str(WORKSPACE), "apply", str(diff_path)],
        capture_output=True, text=True,
    )
    ok = apply.returncode == 0
    return {
        "apply_ok": ok,
        "apply_error": "" if ok else apply.stderr[-2000:],
    }