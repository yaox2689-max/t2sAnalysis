"""Tests for tracing, logging, and evaluation framework."""

import json
from unittest.mock import MagicMock, patch

import pytest

from app.core.tracing import new_trace_id, trace_node


# ── Tracing tests ───────────────────────────────────────


class TestTraceID:
    def test_format(self):
        tid = new_trace_id()
        assert tid.startswith("tx_")
        assert len(tid) == 15  # tx_ + 12 hex chars

    def test_unique(self):
        ids = {new_trace_id() for _ in range(100)}
        assert len(ids) == 100


class TestTraceNode:
    async def test_logs_start_and_end(self):
        """trace_node decorator logs start + end events."""
        tid = new_trace_id()

        @trace_node("test_node", tid)
        async def dummy():
            return 42

        with patch("app.core.tracing.logger") as mock_logger:
            result = await dummy()
            assert result == 42

            # Expect 2 log calls: start + end
            assert mock_logger.info.call_count == 2

            start_call = mock_logger.info.call_args_list[0][0][0]
            assert start_call["trace_id"] == tid
            assert start_call["node"] == "test_node"
            assert start_call["event"] == "node_start"

            end_call = mock_logger.info.call_args_list[1][0][0]
            assert end_call["trace_id"] == tid
            assert end_call["node"] == "test_node"
            assert end_call["event"] == "node_end"
            assert end_call["success"] is True
            assert "elapsed_ms" in end_call

    async def test_logs_error(self):
        """trace_node logs error on exception."""
        tid = new_trace_id()

        @trace_node("failing_node", tid)
        async def failing():
            raise ValueError("something broke")

        with patch("app.core.tracing.logger") as mock_logger:
            with pytest.raises(ValueError, match="something broke"):
                await failing()

            # Expect 1 info (start) + 1 error (end with error)
            assert mock_logger.info.call_count == 1
            assert mock_logger.error.call_count == 1

            error_call = mock_logger.error.call_args[0][0]
            assert error_call["success"] is False
            assert "something broke" in error_call["error"]

    async def test_attempt_and_parent(self):
        """trace_node passes attempt and parent_trace_id through."""
        tid = new_trace_id()

        @trace_node("reflect", tid, attempt=2, parent_trace_id=tid)
        async def reflect():
            return "done"

        with patch("app.core.tracing.logger") as mock_logger:
            await reflect()

            start_call = mock_logger.info.call_args_list[0][0][0]
            assert start_call["attempt"] == 2
            assert start_call["parent_trace_id"] == tid


# ── JSON logger tests ───────────────────────────────────


class TestJSONLogger:
    def test_json_output(self):
        """Logger writes valid JSON with timestamp and level."""
        import io
        import logging
        from app.core.logging import logger, JSONFormatter

        buf = io.StringIO()
        handler = logging.StreamHandler(buf)
        handler.setFormatter(JSONFormatter())
        logger.addHandler(handler)

        logger.info({"trace_id": "tx_test", "node": "analyze", "event": "node_start"})
        data = json.loads(buf.getvalue().strip())
        assert data["level"] == "INFO"
        assert data["trace_id"] == "tx_test"
        assert data["node"] == "analyze"
        assert data["event"] == "node_start"
        assert "timestamp" in data

        logger.removeHandler(handler)


# ── Evaluation tests ────────────────────────────────────


@pytest.fixture
def sample_case():
    return {
        "id": "001",
        "question": "test",
        "category": "aggregation",
        "difficulty": "easy",
        "expected_tables": ["orders", "payments"],
        "expected_metrics": ["sales"],
        "expected_dimensions": ["category"],
        "requires_chart": True,
    }


class TestMetrics:
    def test_task_accuracy_perfect(self, sample_case):
        plan = MagicMock()
        plan.task_type = "aggregation"
        plan.metrics = ["sales"]
        plan.dimensions = ["category"]
        from evaluation.metrics import score_task_accuracy
        assert score_task_accuracy(plan, sample_case) == 1.0

    def test_task_accuracy_zero(self, sample_case):
        from evaluation.metrics import score_task_accuracy
        assert score_task_accuracy(None, sample_case) == 0.0

    def test_sql_executable(self):
        from evaluation.metrics import score_sql_executable
        qr = MagicMock()
        qr.columns = ["sales"]
        qr.rows = [{"sales": 100}]
        assert score_sql_executable(None, qr) == 1.0
        assert score_sql_executable(None, None) == 0.0

    def test_sql_valid(self):
        from evaluation.metrics import score_sql_valid
        vr = MagicMock()
        vr.passed = True
        assert score_sql_valid(vr) == 1.0
        vr.passed = False
        assert score_sql_valid(vr) == 0.0

    def test_result_consistency(self, sample_case):
        from evaluation.metrics import score_result_consistency
        qr = MagicMock()
        qr.columns = ["category", "total_sales"]
        score = score_result_consistency(qr, sample_case)
        assert score > 0.5

    def test_result_consistency_none(self, sample_case):
        from evaluation.metrics import score_result_consistency
        assert score_result_consistency(None, sample_case) == 0.0

    def test_latency_score(self):
        from evaluation.metrics import compute_latency
        assert compute_latency(500) == 1.0
        assert compute_latency(5000) == pytest.approx(0.625, rel=0.1)
        assert compute_latency(15000) == 0.0

    def test_aggregate(self):
        from evaluation.metrics import aggregate
        results = [
            {"task_accuracy": 0.8, "sql_executable": 1.0, "sql_valid": 1.0,
             "result_consistency": 1.0, "elapsed_ms": 1500, "retry_count": 0},
            {"task_accuracy": 0.6, "sql_executable": 0.0, "sql_valid": 1.0,
             "result_consistency": 0.5, "elapsed_ms": 3000, "retry_count": 1},
        ]
        report = aggregate(results)
        assert report.total == 2
        assert report.task_accuracy == 0.7
        assert report.sql_executable == 0.5
        assert report.avg_latency_ms == 2250
        assert report.avg_retry_count == 0.5


class TestRunner:
    async def test_runner_with_mock(self):
        from evaluation.runner import run, load_dataset

        dataset = load_dataset()
        assert len(dataset) >= 5  # at least 5 cases

        class MockOutput:
            task_plan = None
            generated_sql = None
            validation_result = None
            query_result = None
            retry_count = 0
            elapsed_ms = 0.0

        async def mock_agent(question: str):
            return MockOutput()

        report = await run(mock_agent, dataset=dataset)
        assert report.total == len(dataset)
        assert 0 <= report.task_accuracy <= 1
        assert report.avg_retry_count == 0
