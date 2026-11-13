from langgraph.types import interrupt
from orchestrator.state import HarnessState
from orchestrator.llm import LLM


async def reviewer_node(state: HarnessState) -> dict:
    llm = LLM()
    decision, comment = await llm.review(state["diff"])

    # Автоматический reject не требует человека.
    if decision == "reject":
        return {"review_decision": "reject", "review_comment": comment}

    # Approve — через human-in-the-loop gate.
    human = interrupt({
        "question": "Применить diff?",
        "diff": state["diff"],
        "llm_comment": comment,
        "thread_id": "see config",
    })

    if human is True or human == "approve":
        return {"review_decision": "approve", "review_comment": "approved by human"}
    return {
        "review_decision": "reject",
        "review_comment": f"human rejected: {human}",
    }