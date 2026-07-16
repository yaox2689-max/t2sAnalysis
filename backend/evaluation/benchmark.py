#!/usr/bin/env python3
"""Benchmark CLI — run the golden dataset against the full LangGraph Workflow.

Usage:
    cd backend
    python -m evaluation.benchmark
    # → prints report + writes evaluation/report.json
"""

import asyncio
import json
import os
from datetime import datetime, timezone


async def _build_and_run():
    """Build the Workflow graph and run the benchmark."""
    # We import lazily so that missing dependencies don't break
    # the import of this module itself.
    from evaluation import runner

    # NOTE: In a full integration setup, replace the mock agent
    # below with the real LangGraph Workflow.
    #
    #   from app.graph.graph import build_graph
    #   from app.services.task_analyzer import TaskAnalyzer
    #   from app.schemas.schema_retriever import SchemaRetriever
    #   ...
    #
    # For now, the mock verifies the runner + metrics are wired
    # correctly.

    class MockOutput:
        task_plan = None
        generated_sql = None
        validation_result = None
        query_result = None
        retry_count = 0
        elapsed_ms = 0.0

    async def mock_agent(question: str) -> MockOutput:
        return MockOutput()

    report = await runner.run(mock_agent)

    # Print summary
    print(f"\n{'='*50}")
    print(f"  Benchmark Report — {datetime.now(timezone.utc).isoformat()}")
    print(f"{'='*50}")
    print(f"  Total cases:       {report.total}")
    print(f"  Task Accuracy:     {report.task_accuracy:.2%}")
    print(f"  SQL Executable:    {report.sql_executable:.2%}")
    print(f"  SQL Valid:         {report.sql_valid:.2%}")
    print(f"  Result Consistency:{report.result_consistency:.2%}")
    print(f"  Avg Latency:       {report.avg_latency_ms:.0f} ms")
    print(f"  Avg Retry Count:   {report.avg_retry_count:.2f}")
    print(f"{'='*50}\n")

    # Write report
    report_path = os.path.join(os.path.dirname(__file__), "report.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "total": report.total,
            "task_accuracy": report.task_accuracy,
            "sql_executable": report.sql_executable,
            "sql_valid": report.sql_valid,
            "result_consistency": report.result_consistency,
            "avg_latency_ms": report.avg_latency_ms,
            "avg_retry_count": report.avg_retry_count,
            "details": [
                {k: d[k] for k in ("id", "question", "task_accuracy", "sql_executable",
                                   "sql_valid", "result_consistency", "elapsed_ms", "retry_count")}
                for d in (report.details or [])
            ],
        }, f, ensure_ascii=False, indent=2)

    print(f"  Report written to: {report_path}")
    return report


if __name__ == "__main__":
    asyncio.run(_build_and_run())
