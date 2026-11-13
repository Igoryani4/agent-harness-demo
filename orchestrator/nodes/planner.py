from orchestrator.state import HarnessState
from orchestrator.llm import LLM


async def planner_node(state: HarnessState) -> dict:
    llm = LLM()
    plan = await llm.plan(state["objective"])
    return {"plan": plan}