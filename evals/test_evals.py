import asyncio
import yaml
import pytest
from pathlib import Path
import subprocess
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.types import Command

from orchestrator.graph import build_graph
from orchestrator.state import initial_state, DB_PATH

CASES = yaml.safe_load(open("evals/cases.yaml"))


@pytest.fixture(autouse=True)
def reset_workspace():
    subprocess.run(
        ["git", "-C", str(Path("workspace").resolve()), "checkout", "--", "."],
        capture_output=True,
    )
    yield


@pytest.mark.parametrize("case", CASES, ids=[c["id"] for c in CASES])
def test_harness_case(case):
    async def _run():
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        async with AsyncSqliteSaver.from_conn_string(str(DB_PATH)) as cp:
            await cp.setup()
            graph = build_graph(cp)
            cfg = {"configurable": {"thread_id": f"eval-{case['id']}"}}
            result = await graph.ainvoke(
                initial_state(case["objective"], case.get("max_iterations", 2)),
                cfg,
            )
            # Авто-approve, если граф остановился на interrupt
            if result.get("__interrupt__"):
                result = await graph.ainvoke(Command(resume=True), cfg)
            return result

    result = asyncio.run(_run())

    if "expect_test_passed" in case:
        assert (result.get("test_result") or {}).get("passed") == case["expect_test_passed"]
    if "expect_review_decision" in case:
        assert result["review_decision"] == case["expect_review_decision"]
    if "max_diff_lines" in case:
        diff_lines = [
            l for l in result.get("diff", "").splitlines()
            if l.startswith(("+", "-")) and not l.startswith(("+++", "---"))
        ]
        assert len(diff_lines) <= case["max_diff_lines"]