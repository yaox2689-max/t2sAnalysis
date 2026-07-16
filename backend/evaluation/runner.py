"""Evaluation runner — executes a benchmark dataset against any agent function.

The runner is agnostic to whether the agent is a full LangGraph Workflow,
a mock, or a single module.  It only expects:

    async def agent_fn(question: str) -> AgentOutput

Where AgentOutput is a dict-like object with at least:
    task_plan, generated_sql, validation_result, query_result,
    retry_count, elapsed_ms
"""

import json
import os
import time
from typing import Any, Callable, Optional

from evaluation.metrics import (
    EvaluationReport,
    aggregate,
    score_result_consistency,
    score_sql_executable,
    score_sql_valid,
    score_task_accuracy,
)

DATASET_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dataset.json")


def load_dataset(path: Optional[str] = None) -> list[dict]:
    """Load the golden dataset from a JSON file."""
    p = path or DATASET_PATH
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)


async def run(
    agent_fn: Callable[[str], Any],
    dataset: Optional[list[dict]] = None,
    dataset_path: Optional[str] = None,
) -> EvaluationReport:
    """Run the benchmark dataset against an agent function.

    Args:
        agent_fn: async function that accepts ``question: str`` and
                  returns an object (dict or namespace) with fields:
                  task_plan, generated_sql, validation_result,
                  query_result, retry_count, elapsed_ms.
        dataset: optional pre-loaded dataset list; if omitted,
                 loads from *dataset_path* (defaults to dataset.json).

    Returns:
        An EvaluationReport with aggregated metrics.
    """
    cases = dataset or load_dataset(dataset_path)
    results: list[dict] = []

    for case in cases:
        start = time.perf_counter()
        try:
            output = await agent_fn(case["question"])
        except Exception as exc:
            output = type("AgentOutput", (), {
                "task_plan": None,
                "generated_sql": None,
                "validation_result": None,
                "query_result": None,
                "retry_count": 0,
                "elapsed_ms": (time.perf_counter() - start) * 1000,
                "error": str(exc),
            })

        elapsed_ms = getattr(output, "elapsed_ms", None)
        if elapsed_ms is None:
            elapsed_ms = (time.perf_counter() - start) * 1000

        result = {
            "id": case["id"],
            "question": case["question"],
            "task_accuracy": score_task_accuracy(getattr(output, "task_plan", None), case),
            "sql_executable": score_sql_executable(getattr(output, "generated_sql", None), getattr(output, "query_result", None)),
            "sql_valid": score_sql_valid(getattr(output, "validation_result", None)),
            "result_consistency": score_result_consistency(getattr(output, "query_result", None), case),
            "elapsed_ms": round(elapsed_ms, 2),
            "retry_count": getattr(output, "retry_count", 0),
        }
        results.append(result)

    return aggregate(results)
