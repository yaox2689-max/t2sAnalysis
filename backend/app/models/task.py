"""Task plan models for Task Analyzer output."""

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
