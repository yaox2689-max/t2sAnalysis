"""Graph conditional routers — pure functions that map ``AgentState`` → next node name.

Every router is a plain function (not a node).  LangGraph calls them
after a node finishes to decide which edge to follow.
"""

from app.agents.state import AgentState


def route_after_validate(state: AgentState) -> str:
    """After validation: pass → execute, fail → reflect."""
    validation = state.get("validation_result")
    if validation is None or not validation.passed:
        return "reflect"
    return "execute"


def route_after_execute(state: AgentState) -> str:
    """After execution: success → end, failure → reflect.

    Also checks retry budget — if exhausted, end immediately.
    """
    retry_count = state.get("retry_count") or 0
    max_retries = state.get("max_retries") or 3
    if retry_count >= max_retries:
        return "end"

    result = state.get("query_result")
    if result is not None:
        return "end"
    return "reflect"


def route_after_reflection(state: AgentState) -> str:
    """After reflection: dispatch based on ``next_action``.

    - ``stop`` → end (max retries exhausted or unrecoverable error)
    - ``retry_generate`` → re-run generate node
    - ``retry_retrieve`` → re-run retrieve node, then generate

    Also guards the retry budget — if exhausted, go to end.
    """
    retry_count = state.get("retry_count") or 0
    max_retries = state.get("max_retries") or 3
    if retry_count >= max_retries:
        return "end"

    action = state.get("next_action") or "stop"
    if action == "retry_generate":
        return "generate"
    if action == "retry_retrieve":
        return "retrieve"
    return "end"
