"""Evaluation metrics — scoring functions for benchmark results.

Each metric is a pure function that accepts raw results and returns
a score (float 0.0–1.0 or absolute number).
"""

from typing import Any, Optional


def score_task_accuracy(
    task_plan: Any,
    expected: dict,
) -> float:
    """Score how well the TaskPlan matches the expected dimensions.

    Checks:
    - expected_tables overlap with generated tables
    - expected_metrics overlap with generated metrics
    - category match (if available)
    Returns a float 0.0–1.0.
    """
    if task_plan is None:
        return 0.0

    score = 0.0
    total_checks = 0

    # Category match
    if "category" in expected:
        total_checks += 1
        expected_cat = expected["category"]
        actual_cat = getattr(task_plan, "task_type", None)
        if actual_cat and expected_cat in actual_cat:
            score += 1.0

    # Metrics overlap
    if expected.get("expected_metrics"):
        total_checks += 1
        expected_metrics = set(expected["expected_metrics"])
        actual_metrics = set(getattr(task_plan, "metrics", []))
        if actual_metrics:
            overlap = len(expected_metrics & actual_metrics)
            score += overlap / len(expected_metrics)

    # Dimensions overlap
    if expected.get("expected_dimensions"):
        total_checks += 1
        expected_dims = set(expected["expected_dimensions"])
        actual_dims = set(getattr(task_plan, "dimensions", []))
        if actual_dims:
            overlap = len(expected_dims & actual_dims)
            score += overlap / len(expected_dims)

    return score / total_checks if total_checks > 0 else 0.0


def score_sql_executable(
    generated_sql: Any,
    query_result: Any,
) -> float:
    """Score whether SQL executed successfully (1.0) or failed (0.0)."""
    if query_result is not None:
        return 1.0
    if generated_sql is not None and hasattr(generated_sql, "valid"):
        return 1.0 if generated_sql.valid else 0.0
    return 0.0


def score_sql_valid(
    validation_result: Any,
) -> float:
    """Score whether SQL passed validation (1.0) or not (0.0)."""
    if validation_result is None:
        return 0.0
    return 1.0 if getattr(validation_result, "passed", False) else 0.0


def score_result_consistency(
    query_result: Any,
    expected: dict,
) -> float:
    """Score how well the QueryResult matches expectations.

    Checks column presence — does not compare exact values.
    Returns 0.0 if no result, otherwise a 0.0–1.0 score.
    """
    if query_result is None:
        return 0.0

    columns = getattr(query_result, "columns", None)
    if not columns:
        return 0.0

    expected_tables = expected.get("expected_tables", [])
    expected_metrics = expected.get("expected_metrics", [])

    # Score column presence: do our result columns look related to what was asked?
    # We don't have expected column names per se, so we check:
    # - result has both metric-like and dimension-like columns
    column_set = {c.lower() for c in columns}
    num_metric_cols = sum(
        1 for m in expected_metrics if any(m.lower() in c for c in column_set)
    )

    if not column_set:
        return 0.0
    if num_metric_cols > 0:
        return 1.0
    return 0.5  # has columns but can't clearly match


def compute_latency(elapsed_ms: float) -> float:
    """Convert latency to a score (0.0–1.0).

    < 2s = 1.0, 2–10s = linear decay, > 10s = 0.0.
    """
    if elapsed_ms < 2000:
        return 1.0
    if elapsed_ms > 10000:
        return 0.0
    return 1.0 - (elapsed_ms - 2000) / 8000


# ── Aggregate ───────────────────────────────────────────


class EvaluationReport:
    """Aggregated results from a benchmark run."""

    def __init__(
        self,
        total: int = 0,
        task_accuracy: float = 0.0,
        sql_executable: float = 0.0,
        sql_valid: float = 0.0,
        result_consistency: float = 0.0,
        avg_latency_ms: float = 0.0,
        avg_retry_count: float = 0.0,
        details: Optional[list[dict]] = None,
    ) -> None:
        self.total = total
        self.task_accuracy = task_accuracy
        self.sql_executable = sql_executable
        self.sql_valid = sql_valid
        self.result_consistency = result_consistency
        self.avg_latency_ms = avg_latency_ms
        self.avg_retry_count = avg_retry_count
        self.details = details or []


def aggregate(results: list[dict]) -> EvaluationReport:
    """Aggregate per-case results into a final EvaluationReport."""
    n = len(results)
    if n == 0:
        return EvaluationReport()

    task_scores = []
    sql_exec_scores = []
    sql_valid_scores = []
    result_scores = []
    latencies = []
    retries = []

    for r in results:
        task_scores.append(r.get("task_accuracy", 0.0))
        sql_exec_scores.append(r.get("sql_executable", 0.0))
        sql_valid_scores.append(r.get("sql_valid", 0.0))
        result_scores.append(r.get("result_consistency", 0.0))
        latencies.append(r.get("elapsed_ms", 0.0))
        retries.append(r.get("retry_count", 0))

    return EvaluationReport(
        total=n,
        task_accuracy=sum(task_scores) / n,
        sql_executable=sum(sql_exec_scores) / n,
        sql_valid=sum(sql_valid_scores) / n,
        result_consistency=sum(result_scores) / n,
        avg_latency_ms=sum(latencies) / n,
        avg_retry_count=sum(retries) / n,
        details=results,
    )
