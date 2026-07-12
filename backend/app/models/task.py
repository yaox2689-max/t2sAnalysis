"""Task plan models for Task Analyzer and SQL generation output."""

from typing import Optional

from pydantic import BaseModel


class TaskPlan(BaseModel):
    """Structured task description produced by TaskAnalyzer.

    This is the output contract between TaskAnalyzer and downstream
    components (SQL Generation, Chart Tool, Insight Tool).
    """

    task_type: str
    time_range: Optional[dict] = None
    metrics: list[str] = []
    dimensions: list[str] = []
    requires_chart: bool = False
    chart_type_hint: Optional[str] = None
    requires_insight: bool = False


class SchemaContext(BaseModel):
    """Schema information for a set of tables relevant to a question.

    Built by SchemaRepository / SchemaRetriever and consumed by
    SQLGenerator to construct the LLM prompt.
    """

    tables: list[str]
    columns: dict[str, list[dict]]  # table_name → [{column_name, data_type, comment}]
    relationships: list[str] = []   # human-readable FK descriptions
    sample_rows: dict[str, list[dict]] = {}  # table_name → [{col: val}]


class GeneratedSQL(BaseModel):
    """Output from SQLGenerator — a single generated SQL statement.

    This is the input contract for SQLValidator.
    """

    sql: str
    explanation: str = ""
    valid: bool = True
