"""LangGraph workflow nodes — thin wrappers around existing modules.

Each node:
1. Reads the fields it needs from ``state``.
2. Calls the corresponding module (injected at build time).
3. Writes results back to ``state``.

No business logic lives here — every node delegates entirely to
a dedicated Repository, Service, Tool, or Agent module.
"""

from app.agents.state import AgentState
from app.models.query import QueryResult
from app.models.task import GeneratedSQL, SchemaContext, TaskPlan
from app.tools.sql_validator import ValidationResult


def _first_error(state: AgentState) -> str:
    errors = state.get("errors") or []
    return errors[0] if errors else "Unknown error"


async def analyze_task_node(
    state: AgentState,
    analyzer: object,
) -> dict:
    """Call TaskAnalyzer and write ``task_plan`` into state."""
    question = state["question"]
    history = state.get("history") or []
    plan: TaskPlan = await analyzer.analyze(question, history)  # type: ignore[union-attr]
    return {"task_plan": plan}


async def retrieve_schema_node(
    state: AgentState,
    retriever: object,
) -> dict:
    """Call SchemaRetriever and write ``schema_context`` into state."""
    question = state["question"]
    ctx: SchemaContext = await retriever.retrieve(question)  # type: ignore[union-attr]
    return {"schema_context": ctx}


async def generate_sql_node(
    state: AgentState,
    generator: object,
) -> dict:
    """Call SQLGenerator and write ``generated_sql`` + ``current_sql``."""
    plan = state["task_plan"]
    ctx = state["schema_context"]
    result: GeneratedSQL = await generator.generate(plan, ctx)  # type: ignore[union-attr]
    return {
        "generated_sql": result,
        "current_sql": result.sql,
    }


async def validate_sql_node(
    state: AgentState,
    validator: object,
) -> dict:
    """Call SQLValidator and write ``validation_result`` into state.

    On failure, write validation warnings to ``errors`` so the
    reflection node can act on them.
    """
    sql = state.get("current_sql") or ""
    result: ValidationResult = validator.validate(sql)  # type: ignore[union-attr]
    updates: dict = {"validation_result": result}
    if not result.passed:
        msg = "; ".join(result.warnings) if result.warnings else "Validation failed"
        updates["errors"] = (state.get("errors") or []) + [msg]
    return updates


async def execute_sql_node(
    state: AgentState,
    executor: object,
) -> dict:
    """Call SafeExecutor and write ``query_result`` into state.

    On error, appends the error message to ``errors``.
    """
    sql = state.get("current_sql") or ""
    try:
        result: QueryResult = await executor.execute(sql)  # type: ignore[union-attr]
        return {"query_result": result}
    except Exception as exc:
        return {
            "query_result": None,
            "errors": (state.get("errors") or []) + [str(exc)],
        }


async def reflect_node(
    state: AgentState,
    reflection: object,
) -> dict:
    """Call ReflectionLoop and write ``current_sql`` + ``retry_count`` + ``next_action``.

    The ``next_action`` field tells the graph router whether to
    retry generate, retry retrieve, or stop.
    """
    question = state["question"]
    sql = state.get("current_sql") or ""
    error = _first_error(state)
    plan = state["task_plan"]
    ctx = state["schema_context"]
    max_retries = state.get("max_retries") or 3

    result = await reflection.run(  # type: ignore[union-attr]
        question, sql, error, plan, ctx, max_retries=max_retries,
    )
    retry_count = (state.get("retry_count") or 0) + 1

    return {
        "current_sql": result.final_sql,
        "retry_count": retry_count,
        "next_action": result.next_action,
        "errors": [],
    }
