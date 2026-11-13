from orchestrator.state import HarnessState
from orchestrator.mcp_client import MCPTools


async def tester_node(state: HarnessState) -> dict:
    if not state.get("apply_ok"):
        # Если diff не применился — тесты гонять бессмысленно.
        return {"test_result": {"passed": False, "failed": -1, "output": "diff not applied"}}

    tools = MCPTools()
    result = await tools.run_tests("tests")
    return {"test_result": result}