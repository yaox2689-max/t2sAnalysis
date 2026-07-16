"""Tests for Evidence Analyzer — result formatting, LLM analysis, edge cases."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.query import QueryResult
from app.tools.evidence_analyzer import (
    EvidenceAnalyzer,
    _format_result,
)


# ── _format_result tests ────────────────────────────────


class TestFormatResult:
    def test_empty(self):
        text = _format_result(QueryResult(columns=[], rows=[]))
        assert "Rows: 0" in text

    def test_basic(self):
        result = QueryResult(
            columns=["category", "sales"],
            rows=[{"category": "A", "sales": 100}, {"category": "B", "sales": 200}],
        )
        text = _format_result(result, label="primary")
        assert "[primary]" in text
        assert "Preview" in text
        assert "avg=150.00" in text
        assert "2 distinct" in text


# ── _parse tests ────────────────────────────────────────


class TestParse:
    def test_valid_json(self):
        raw = """{
            "conclusion": "Sales declined due to electronics.",
            "evidence_chain": [
                {"claim": "Electronics fell 32%", "data": ["¥5.3M to ¥3.6M"],
                 "source": "primary vs comparison", "strength": 0.92}
            ],
            "suggestions": ["Check electronics"],
            "limitations": ["No inventory data"]
        }"""
        report = EvidenceAnalyzer._parse(raw)
        assert report.conclusion == "Sales declined due to electronics."
        assert len(report.evidence_chain) == 1
        assert report.evidence_chain[0].strength == 0.92
        assert "Check electronics" in report.suggestions
        assert "No inventory data" in report.limitations

    def test_invalid_json_fallback(self):
        report = EvidenceAnalyzer._parse("not json")
        assert report.conclusion == "not json"
        assert report.evidence_chain == []

    def test_empty_json(self):
        report = EvidenceAnalyzer._parse("{}")
        assert report.conclusion == ""
        assert report.evidence_chain == []


# ── analyze tests (mock LLM) ────────────────────────────


def _mock_llm(content: str):
    msg = MagicMock()
    msg.content = content
    choice = MagicMock()
    choice.message = msg
    resp = MagicMock()
    resp.choices = [choice]
    return resp


SAMPLE_PRIMARY = QueryResult(
    columns=["category", "sales"],
    rows=[{"category": "Electronics", "sales": 360},
          {"category": "Clothing", "sales": 200}],
)
SAMPLE_COMPARISON = QueryResult(
    columns=["category", "sales"],
    rows=[{"category": "Electronics", "sales": 530},
          {"category": "Clothing", "sales": 210}],
)


@pytest.fixture
def analyzer():
    a = EvidenceAnalyzer(api_key="test", model="test-model", base_url="http://fake")
    a._client.chat.completions.create = AsyncMock()
    return a


class TestAnalyze:
    async def test_empty_primary_returns_early(self, analyzer):
        """Empty primary data returns early without LLM call."""
        report = await analyzer.analyze(
            "为什么销量下降", QueryResult(columns=["a"], rows=[]),
        )
        assert "数据不足" in report.conclusion
        analyzer._client.chat.completions.create.assert_not_called()

    async def test_primary_only_no_comparison(self, analyzer):
        """Analyse with only primary data still produces a report."""
        analyzer._client.chat.completions.create.return_value = _mock_llm(
            '{"conclusion": "Electronics dominates sales.", "evidence_chain": []}'
        )
        report = await analyzer.analyze("What sold most?", SAMPLE_PRIMARY)
        assert report.conclusion == "Electronics dominates sales."
        analyzer._client.chat.completions.create.assert_called_once()

    async def test_dual_result(self, analyzer):
        """Both primary and comparison data are presented."""
        analyzer._client.chat.completions.create.return_value = _mock_llm(
            """{"conclusion": "Electronics declined.",
                "evidence_chain": [{"claim": "Electronics: 360 vs 530",
                                    "data": ["32% drop"], "source": "comparison",
                                    "strength": 0.9}],
                "suggestions": ["Investigate"],
                "limitations": ["No inventory data"]}"""
        )
        report = await analyzer.analyze(
            "Why did sales drop?",
            SAMPLE_PRIMARY,
            comparison_result=SAMPLE_COMPARISON,
        )
        assert report.conclusion == "Electronics declined."
        assert len(report.evidence_chain) == 1
        assert report.evidence_chain[0].strength == 0.9
        assert len(report.suggestions) == 1
        assert len(report.limitations) == 1

    async def test_evaluates_prompt_includes_both_datasets(self, analyzer):
        """Prompt contains both primary and comparison data."""
        analyzer._client.chat.completions.create.return_value = _mock_llm(
            '{"conclusion": "Decline noted."}'
        )
        await analyzer.analyze("Why?", SAMPLE_PRIMARY, SAMPLE_COMPARISON)
        call_args = analyzer._client.chat.completions.create.call_args
        messages = call_args[1]["messages"]
        user_msg = messages[1]["content"]
        assert "[primary]" in user_msg
        assert "[comparison]" in user_msg

    async def test_non_json_response_fallback(self, analyzer):
        analyzer._client.chat.completions.create.return_value = _mock_llm(
            "Plain text response"
        )
        report = await analyzer.analyze("Why?", SAMPLE_PRIMARY)
        assert report.conclusion == "Plain text response"
        assert report.evidence_chain == []

    async def test_empty_evidence_chain_valid(self, analyzer):
        """Evidence chain can be empty — still a valid report."""
        analyzer._client.chat.completions.create.return_value = _mock_llm(
            '{"conclusion": "No clear pattern.", "evidence_chain": []}'
        )
        report = await analyzer.analyze("Why?", SAMPLE_PRIMARY)
        assert report.conclusion == "No clear pattern."
        assert report.evidence_chain == []
