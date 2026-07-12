"""Tests for TaskAnalyzer — parsing, fallback, integration with mock LLM."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.task import TaskPlan
from app.services.task_analyzer import TaskAnalyzer


@pytest.fixture
def analyzer():
    return TaskAnalyzer(api_key="test-key", model="test-model", base_url="http://fake")


def _mock_response(content: str):
    """Build a mock OpenAI response object."""
    msg = MagicMock()
    msg.content = content
    choice = MagicMock()
    choice.message = msg
    resp = MagicMock()
    resp.choices = [choice]
    return resp


class TestParse:
    def test_parse_valid_json(self, analyzer):
        raw = '{"task_type": "trend_analysis", "metrics": ["sales"], "requires_chart": true}'
        plan = analyzer._parse(raw)
        assert plan.task_type == "trend_analysis"
        assert plan.metrics == ["sales"]
        assert plan.requires_chart is True

    def test_parse_with_time_range(self, analyzer):
        raw = (
            '{"task_type": "comparison", "time_range": {"start": "2026-01-01", '
            '"end": "2026-01-31"}, "metrics": ["revenue"], '
            '"dimensions": ["category"], "requires_chart": true, '
            '"chart_type_hint": "bar", "requires_insight": false}'
        )
        plan = analyzer._parse(raw)
        assert plan.task_type == "comparison"
        assert plan.time_range == {"start": "2026-01-01", "end": "2026-01-31"}
        assert plan.chart_type_hint == "bar"

    def test_parse_invalid_json_fallback(self, analyzer):
        plan = analyzer._parse("not json at all")
        assert plan.task_type == "unknown"
        assert plan.metrics == []

    def test_parse_empty_string_fallback(self, analyzer):
        plan = analyzer._parse("")
        assert plan.task_type == "unknown"

    def test_parse_partial_fills_defaults(self, analyzer):
        raw = '{"task_type": "rank"}'
        plan = analyzer._parse(raw)
        assert plan.task_type == "rank"
        assert plan.metrics == []
        assert plan.requires_chart is False


@pytest.mark.asyncio
async def test_analyze_calls_llm_and_returns_taskplan(analyzer):
    fake = _mock_response(
        '{"task_type": "trend_analysis", '
        '"time_range": {"start": "2026-06-12", "end": "2026-07-12"}, '
        '"metrics": ["sales_amount"], '
        '"dimensions": ["product_category"], '
        '"requires_chart": true, '
        '"chart_type_hint": "line", '
        '"requires_insight": false}'
    )

    with patch.object(analyzer.client.chat.completions, "create", new=AsyncMock(return_value=fake)):
        plan = await analyzer.analyze("最近30天各品类销售额趋势")

    assert plan.task_type == "trend_analysis"
    assert plan.metrics == ["sales_amount"]
    assert plan.dimensions == ["product_category"]
    assert plan.requires_chart is True
    assert plan.chart_type_hint == "line"


@pytest.mark.asyncio
async def test_analyze_fallback_on_invalid_llm_response(analyzer):
    with patch.object(
        analyzer.client.chat.completions,
        "create",
        new=AsyncMock(return_value=_mock_response("sorry i cannot do that")),
    ):
        plan = await analyzer.analyze("some question")

    assert plan.task_type == "unknown"
