from orchestrator.state import HarnessState
from orchestrator.llm import LLM
from orchestrator.mcp_client import MCPTools


async def coder_node(state: HarnessState) -> dict:
    llm = LLM()
    tools = MCPTools()

    obj = state["objective"]
    target = obj.split()[-1].split("/")[-1] if obj.split() else ""
    base = target.replace("Test", "")

    files = []
    try:
        # Ищем и тест, и production-класс
        for name in [target, base]:
            if not name:
                continue
            hits = await tools.search_codebase(name, path=".", max_results=10)
            for h in hits or []:
                if not isinstance(h, dict) or "file" not in h:
                    continue
                f = h["file"]
                if not f.endswith(".java") or f in [x[0] for x in files]:
                    continue
                try:
                    content = await tools.read_file(f)
                    files.append((f, content))
                except Exception:
                    pass
        print(f"[coder] files loaded: {[f for f, _ in files]}")
    except Exception as e:
        print(f"[coder] search/read failed: {e}")

    diff = await llm.propose_diff(
        objective=state["objective"],
        plan=state["plan"],
        last_error=(state.get("test_result") or {}).get("output", "")[:2000],
        files=files,
    )

    return {
        "diff": diff,
        "iterations": state.get("iterations", 0) + 1,
    }
