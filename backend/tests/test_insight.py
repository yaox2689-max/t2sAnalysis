"""Tests for Insight Tool — result formatting, LLM summariser, edge cases."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.query import QueryResult
from app.tools.insight import InsightTool, _format_result


# ── _format_result tests ────────────────────────────────


class TestFormatResult:
    def test_empty(self):
        text = _format_result(QueryResult(columns=[], rows=[]))
        assert "Rows: 0" in text
        assert "Statistics" in text

    def test_basic(self):
        result = QueryResult(
            columns=["month", "sales"],
            rows=[
                {"month": "Jan", "sales": 100},
                {"month": "Feb", "sales": 200},
                {"month": "Mar", "sales": 150},
            ],
        )
        text = _format_result(result)
        assert "Rows: 3" in text
        assert "month, sales" in text
        assert "Preview" in text
        assert "min=100.00" in text
        assert "max=200.00" in text
        assert "avg=150.00" in text
        assert "month: non-numeric, 3 distinct" in text

    def test_mixed_types(self):
        result = QueryResult(
            columns=["name", "score"],
            rows=[{"name": "Alice", "score": 85}, {"name": "Bob", "score": 92}],
        )
        text = _format_result(result)
        assert "name: non-numeric, 2 distinct" in text
        assert "avg=88.50" in text


# ── _parse tests ────────────────────────────────────────


class TestParse:
    def test_valid_json(self):
        result = InsightTool._parse(
            '{"summary": "Sales grew 15%", "key_metrics": ["15% growth"], "confidence": 0.85}'
        )
        assert result.summary == "Sales grew 15%"
        assert result.key_metrics == ["15% growth"]
        assert result.confidence == 0.85

    def test_invalid_json_falls_back(self):
        result = InsightTool._parse("not json at all")
        assert result.summary == "not json at all"
        assert result.confidence == 0.0

    def test_empty_json(self):
        result = InsightTool._parse("{}")
        assert len(result.summary) == 0
        assert result.confidence is None


# ── summarize tests (mock LLM) ──────────────────────────


def _mock_llm(content: str):
    msg = MagicMock()
    msg.content = content
    choice = MagicMock()
    choice.message = msg
    resp = MagicMock()
    resp.choices = [choice]
    return resp


@pytest.fixture
def tool():
    t = InsightTool(api_key="test", model="test-model", base_url="http://fake")
    t._client.chat.completions.create = AsyncMock()
    return t


class TestSummarize:
    async def test_empty_rows_returns_early(self, tool):
        """Empty data returns early summary without calling LLM."""
        result = await tool.summarize(
            QueryResult(columns=["a"], rows=[]),
            "test question",
        )
        assert result.summary == "数据不足，无法生成洞察"
        tool._client.chat.completions.create.assert_not_called()

    async def test_calls_llm_with_prompt(self, tool):
        tool._client.chat.completions.create.return_value = _mock_llm(
            '{"summary": "Sales trend is positive.", "key_metrics": [], "confidence": 0.8}'
        )
        result = await tool.summarize(
            QueryResult(columns=["month", "sales"], rows=[{"month": "Jan", "sales": 100}]),
            "销售额趋势",
        )
        assert result.summary == "Sales trend is positive."
        assert result.confidence == 0.8
        # Verify the LLM was called
        call_args = tool._client.chat.completions.create.call_args
        assert call_args is not None
        messages = call_args[1]["messages"]
        assert any("销售额趋势" in m["content"] for m in messages)

    async def test_chart_type_included(self, tool):
        tool._client.chat.completions.create.return_value = _mock_llm(
            '{"summary": "Upward trend.", "confidence": 0.9}'
        )
        result = await tool.summarize(
            QueryResult(columns=["date", "sales"], rows=[{"date": "Jan", "sales": 100}]),
            "趋势",
            chart_type="line",
        )
        assert result.summary == "Upward trend."
        call_args = tool._client.chat.completions.create.call_args
        assert call_args is not None
        messages = call_args[1]["messages"]
        assert any("line" in m["content"] for m in messages)
