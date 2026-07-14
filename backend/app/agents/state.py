"""AgentState — unified context flowing through every LangGraph node.

Each node reads its input fields, calls the corresponding module,
and writes results back.  Fields are typed as ``| None`` so that
every node can validate its preconditions independently.
"""

from typing import Optional, TypedDict

from app.models.query import QueryResult
from app.models.task import GeneratedSQL, SchemaContext, TaskPlan
from app.tools.sql_validator import ValidationResult


class AgentState(TypedDict):
    """State passed between LangGraph nodes in the SQL Agent workflow."""

    question: str
    history: list[dict]

    task_plan: Optional[TaskPlan]
    schema_context: Optional[SchemaContext]
    generated_sql: Optional[GeneratedSQL]
    validation_result: Optional[ValidationResult]
    query_result: Optional[QueryResult]

    current_sql: Optional[str]
    retry_count: int
    max_retries: int
    next_action: Optional[str]

    errors: list[str]
