"""Tests for SQLGenerator — parsing, schema validation, mock LLM."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.agents.sql_generator import SQLGenerator
from app.models.task import SchemaContext, TaskPlan

SAMPLE_SCHEMA = SchemaContext(
    tables=["orders", "customers"],
    columns={
        "orders": [
            {"column_name": "id", "data_type": "int"},
            {"column_name": "customer_id", "data_type": "int"},
            {"column_name": "total", "data_type": "decimal"},
        ],
        "customers": [
            {"column_name": "id", "data_type": "int"},
            {"column_name": "name", "data_type": "varchar"},
        ],
    },
    relationships=["orders.customer_id → customers.id"],
)


@pytest.fixture
def gen():
    return SQLGenerator(api_key="test", model="test-model", base_url="http://fake")


def _mock_response(content: str):
    msg = MagicMock()
    msg.content = content
    choice = MagicMock()
    choice.message = msg
    resp = MagicMock()
    resp.choices = [choice]
    return resp


# ── _parse tests ───────────────────────────────────────

class TestParse:
    def test_parse_valid(self, gen):
        raw = (
            '{"sql": "SELECT id FROM orders", '
            '"explanation": "simple test", '
            '"valid": true}'
        )
        result = gen._parse(raw, SAMPLE_SCHEMA)
        assert result.sql == "SELECT id FROM orders"
        assert result.valid is True

    def test_parse_invalid_json(self, gen):
        result = gen._parse("not json", SAMPLE_SCHEMA)
        assert result.valid is False

    def test_parse_empty_response(self, gen):
        result = gen._parse("", SAMPLE_SCHEMA)
        assert result.valid is False

    def test_parse_schema_violation(self, gen):
        raw = (
            '{"sql": "SELECT id FROM nonexistent_table", '
            '"explanation": "bad sql", '
            '"valid": true}'
        )
        result = gen._parse(raw, SAMPLE_SCHEMA)
        assert result.valid is False
        assert "tables not in the provided schema" in result.explanation

    def test_parse_syntax_error(self, gen):
        raw = (
            '{"sql": "SELECT FROM WHERE", '
            '"explanation": "broken", '
            '"valid": true}'
        )
        result = gen._parse(raw, SAMPLE_SCHEMA)
        assert result.valid is False
        assert "syntax error" in result.explanation.lower()


# ── Integration test (mock LLM) ────────────────────────

@pytest.mark.asyncio
async def test_generate_calls_llm_and_validates(gen):
    task_plan = TaskPlan(
        task_type="simple_query",
        metrics=["total"],
        dimensions=[],
    )

    fake_resp = _mock_response(
        '{"sql": "SELECT COUNT(*) FROM orders", '
        '"explanation": "count all orders", '
        '"valid": true}'
    )

    with patch.object(gen.client.chat.completions, "create", new=AsyncMock(return_value=fake_resp)):
        result = await gen.generate(task_plan, SAMPLE_SCHEMA)

    assert result.valid is True
    assert "SELECT" in result.sql


@pytest.mark.asyncio
async def test_generate_llm_returns_invalid_json(gen):
    task_plan = TaskPlan(task_type="simple_query", metrics=["total"])

    with patch.object(
        gen.client.chat.completions,
        "create",
        new=AsyncMock(return_value=_mock_response("not json")),
    ):
        result = await gen.generate(task_plan, SAMPLE_SCHEMA)

    assert result.valid is False


@pytest.mark.asyncio
async def test_generate_llm_invents_table(gen):
    task_plan = TaskPlan(task_type="simple_query", metrics=["total"])

    fake_resp = _mock_response(
        '{"sql": "SELECT id FROM fake_table", '
        '"explanation": "invented", '
        '"valid": true}'
    )

    with patch.object(
        gen.client.chat.completions,
        "create",
        new=AsyncMock(return_value=fake_resp),
    ):
        result = await gen.generate(task_plan, SAMPLE_SCHEMA)

    assert result.valid is False
    assert "tables not in the provided schema" in result.explanation
