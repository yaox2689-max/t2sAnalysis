"""LangGraph workflow nodes — thin wrappers around existing modules.

Each node:
1. Reads the fields it needs from ``state``.
2. Calls the corresponding module (injected at build time).
3. Writes results back to ``state``.

No business logic lives here — every node delegates entirely to
a dedicated Repository, Service, Tool, or Agent module.
"""

import logging

from app.agents.state import AgentState
from app.core.utils import truncate_error
from app.models.query import QueryResult
from app.models.task import GeneratedSQL, SchemaContext, TaskPlan
from app.tools.sql_validator import ValidationResult

logger = logging.getLogger("t2s_analysis")


def _log(state: AgentState, data: dict) -> dict:
    """Inject trace_id into log data."""
    tid = state.get("trace_id")
    if tid:
        data["trace_id"] = tid
    return data


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
    registry: object = None,
    prompt_builder: object = None,
) -> dict:
    """Build schema context and prompt text for SQL generation.

    Uses DatasetRegistry + PromptBuilder to produce a comprehensive
    prompt with table schemas, column profiles, and sample rows.
    """
    question = state["question"]
    session_id = state.get("session_id")
    user_id = state.get("user_id")

    # New path: DatasetRegistry + PromptBuilder
    if registry is not None and prompt_builder is not None:
        from app.services.dataset_registry import DatasetRegistry
        from app.services.prompt_builder import PromptBuilder
        registry: DatasetRegistry
        prompt_builder: PromptBuilder

        catalog = await registry.get_catalog(session_id=session_id, user_id=user_id, question=question, top_k=30)
        prompt_text = await prompt_builder.build_prompt(catalog)
        available_tables = [t.table_name for t in catalog.tables]

        # Build a minimal SchemaContext for backward compatibility (validation)
        schema_ctx = SchemaContext(
            tables=available_tables,
            columns={
                t.table_name: [{"column_name": c.name, "data_type": c.data_type} for c in t.columns]
                for t in catalog.tables
            },
        )
        return {"schema_context": schema_ctx, "prompt_text": prompt_text}


async def generate_sql_node(
    state: AgentState,
    generator: object,
) -> dict:
    """Call SQLGenerator and write ``generated_sql`` + ``current_sql``."""
    plan = state["task_plan"]
    ctx = state["schema_context"]
    prompt_text = state.get("prompt_text")
    question = state.get("question", "")
    logger.info(_log(state, {"event": "generate_sql_start", "question": question[:100], "tables": ctx.tables if ctx else []}))
    result: GeneratedSQL = await generator.generate(  # type: ignore[union-attr]
        plan, ctx, prompt_text=prompt_text, question=question,
    )
    logger.info(_log(state, {"event": "generate_sql_done", "sql": result.sql[:200], "valid": result.valid}))
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
    """Call DuckDBExecutor and write ``query_result`` into state.

    On error, appends the error message to ``errors``.
    """
    sql = state.get("current_sql") or ""
    session_id = state.get("session_id")
    user_id = state.get("user_id")
    logger.info(_log(state, {"event": "execute_sql_start", "sql": sql[:200]}))
    try:
        result: QueryResult = await executor.execute(  # type: ignore[union-attr]
            sql, session_id=session_id, user_id=user_id,
        )
        logger.info(_log(state, {
            "event": "execute_sql_success",
            "columns": result.columns,
            "row_count": result.row_count,
        }))
        return {"query_result": result}
    except Exception as exc:
        logger.error(_log(state, {"event": "execute_sql_error", "sql": sql[:200], "error": truncate_error(exc)}))
        return {
            "query_result": None,
            "errors": (state.get("errors") or []) + [truncate_error(exc)],
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
