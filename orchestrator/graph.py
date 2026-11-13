import asyncio
from pathlib import Path

from langgraph.graph import StateGraph, START, END
from langgraph.types import Command
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from orchestrator.state import HarnessState, DB_PATH, initial_state
from orchestrator.nodes.planner import planner_node
from orchestrator.nodes.coder import coder_node
from orchestrator.nodes.reviewer import reviewer_node
from orchestrator.nodes.applier import applier_node
from orchestrator.nodes.tester import tester_node


def route_after_review(state: HarnessState) -> str:
    if state["review_decision"] == "approve":
        return "applier"
    if state["iterations"] >= state["max_iterations"]:
        return END
    return "coder"


def route_after_apply(state: HarnessState) -> str:
    return "tester" if state["apply_ok"] else END


def route_after_test(state: HarnessState) -> str:
    if state["test_result"].get("passed"):
        return END
    if state["iterations"] >= state["max_iterations"]:
        return END
    return "coder"


def build_graph(checkpointer):
    builder = StateGraph(HarnessState)

    builder.add_node("planner", planner_node)
    builder.add_node("coder", coder_node)
    builder.add_node("reviewer", reviewer_node)
    builder.add_node("applier", applier_node)
    builder.add_node("tester", tester_node)

    builder.add_edge(START, "planner")
    builder.add_edge("planner", "coder")
    builder.add_edge("coder", "reviewer")
    builder.add_conditional_edges(
        "reviewer", route_after_review,
        {"applier": "applier", "coder": "coder", END: END},
    )
    builder.add_conditional_edges(
        "applier", route_after_apply,
        {"tester": "tester", END: END},
    )
    builder.add_conditional_edges(
        "tester", route_after_test,
        {"coder": "coder", END: END},
    )

    return builder.compile(checkpointer=checkpointer)


async def run(objective: str, thread_id: str = "demo-1", auto_approve: bool = False):
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    async with AsyncSqliteSaver.from_conn_string(str(DB_PATH)) as checkpointer:
        await checkpointer.setup()  # создаёт таблицы, если их нет

        graph = build_graph(checkpointer)
        config = {"configurable": {"thread_id": thread_id}}

        result = await graph.ainvoke(initial_state(objective), config)

        interrupts = result.get("__interrupt__") if isinstance(result, dict) else None
        if interrupts:
            print("PAUSED for review:")
            print(interrupts)
            if auto_approve:
                result = await graph.ainvoke(Command(resume=True), config)
            else:
                answer = input("Approve? [y/N]: ").strip().lower()
                result = await graph.ainvoke(Command(resume=answer == "y"), config)

        print("FINAL:", result)
        return result


if __name__ == "__main__":
    import sys
    objective = sys.argv[1] if len(sys.argv) > 1 else "fix failing test in workspace"
    asyncio.run(run(objective, auto_approve="--yes" in sys.argv))