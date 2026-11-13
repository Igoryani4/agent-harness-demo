from typing import TypedDict, Literal
from pathlib import Path

class HarnessState(TypedDict):
    objective: str
    plan: list[str]
    diff: str
    review_decision: Literal["approve", "reject", ""]
    review_comment: str
    apply_ok: bool
    apply_error: str
    test_result: dict
    iterations: int
    max_iterations: int


DB_PATH = Path("state/harness.db")


def initial_state(objective: str, max_iterations: int = 3) -> HarnessState:
    return {
        "objective": objective,
        "plan": [],
        "diff": "",
        "review_decision": "",
        "review_comment": "",
        "apply_ok": False,
        "apply_error": "",
        "test_result": {},
        "iterations": 0,
        "max_iterations": max_iterations,
    }