"""Tests for Reflection Loop — error classification, handlers, and orchestration."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.agents.reflection import (
    ErrorClassification,
    ErrorClassifier,
    GeneratedSQL,
    ReflectionLoop,
    ReflectionResult,
)
from app.models.task import SchemaContext, TaskPlan


SAMPLE_TASK_PLAN = TaskPlan(
    task_type="aggregation",
    metrics=["total"],
    dimensions=["category"],
)

SAMPLE_SCHEMA = SchemaContext(
    tables=["orders"],
    columns={
        "orders": [
            {"column_name": "id", "data_type": "int"},
            {"column_name": "total", "data_type": "decimal"},
        ]
    },
)


# ── ErrorClassifier tests ───────────────────────────────


def _mock_llm(content: str):
    msg = MagicMock()
    msg.content = content
    choice = MagicMock()
    choice.message = msg
    resp = MagicMock()
    resp.choices = [choice]
    return resp


@pytest.fixture
def classifier():
    client = MagicMock()
    client.chat = MagicMock()
    client.chat.completions = MagicMock()
    client.chat.completions.create = AsyncMock()
    return ErrorClassifier(llm_client=client, model="test-model")


class TestClassifier:
    """ErrorClassifier._parse() unit tests."""

    def test_classify_schema_error(self):
        result = ErrorClassifier._parse(
            '{"error_type": "schema_error", "confidence": 0.95, "detail": "table not found"}'
        )
        assert result.error_type == "schema_error"
        assert result.confidence == 0.95

    def test_classify_syntax_error(self):
        result = ErrorClassifier._parse(
            '{"error_type": "syntax_error", "confidence": 0.9, "detail": "syntax"}'
        )
        assert result.error_type == "syntax_error"

    def test_classify_ambiguous(self):
        result = ErrorClassifier._parse(
            '{"error_type": "ambiguous", "confidence": 0.8, "detail": "ambiguous column"}'
        )
        assert result.error_type == "ambiguous"

    def test_classify_other(self):
        result = ErrorClassifier._parse(
            '{"error_type": "other", "confidence": 0.5, "detail": "timeout"}'
        )
        assert result.error_type == "other"

    def test_classify_invalid_json(self):
        result = ErrorClassifier._parse("not json")
        assert result.error_type == "other"

    async def test_classify_calls_llm(self, classifier):
        """classify() sends error to LLM and returns parsed result."""
        classifier._client.chat.completions.create.return_value = _mock_llm(
            '{"error_type": "syntax_error", "confidence": 0.9, "detail": "SQL syntax error"}'
        )
        result = await classifier.classify("You have an error in your SQL syntax")
        assert result.error_type == "syntax_error"
        assert result.confidence == 0.9

    async def test_classify_fallback_on_bad_response(self, classifier):
        """Non-JSON LLM response falls back to 'other'."""
        classifier._client.chat.completions.create.return_value = _mock_llm(
            "bad response"
        )
        result = await classifier.classify("some error")
        assert result.error_type == "other"


# ── ReflectionLoop tests ────────────────────────────────


class FakeGenerator:
    """Mock SQLGenerator that returns a fixed GeneratedSQL."""

    def __init__(self, result: GeneratedSQL) -> None:
        self._result = result

    async def generate(
        self, task_plan: TaskPlan, schema_context: SchemaContext
    ) -> GeneratedSQL:
        return self._result


class FakeRetriever:
    """Mock SchemaRetriever that returns a fixed context."""

    def __init__(self, context: SchemaContext) -> None:
        self._context = context

    async def retrieve(self, question: str, **kwargs) -> SchemaContext:
        return self._context


def _make_loop(
    classifier_result: ErrorClassification,
) -> ReflectionLoop:
    """Build a ReflectionLoop with a stubbed classifier."""
    loop = ReflectionLoop(
        api_key="test",
        model="test-model",
        base_url="http://fake",
        sql_generator=FakeGenerator(GeneratedSQL(sql="SELECT 1", valid=True)),
        schema_retriever=FakeRetriever(SAMPLE_SCHEMA),
    )
    # Stub the classifier so it returns our desired result directly
    loop._classifier.classify = AsyncMock(return_value=classifier_result)  # type: ignore[assignment]
    return loop


@pytest.mark.asyncio
async def test_loop_success_first_try():
    """syntax_error → handler fixes → success on first attempt."""
    loop = _make_loop(
        classifier_result=ErrorClassification("syntax_error", 0.9, "syntax error"),
    )
    loop._handle_syntax_error = AsyncMock(  # type: ignore[assignment]
        return_value=GeneratedSQL(sql="SELECT id FROM orders", valid=True)
    )

    result = await loop.run(
        question="test",
        sql="SELECT ID FROM orders",
        error_message="Unknown column 'ID'",
        task_plan=SAMPLE_TASK_PLAN,
        schema_context=SAMPLE_SCHEMA,
        max_retries=3,
    )
    assert result.success is True
    assert result.final_sql == "SELECT id FROM orders"
    assert len(result.attempts) == 1


@pytest.mark.asyncio
async def test_loop_exhausts_retries():
    """All retries fail → success=False."""
    loop = _make_loop(
        classifier_result=ErrorClassification("schema_error", 0.9, "schema error"),
    )
    loop._apply_handler = AsyncMock(  # type: ignore[assignment]
        return_value=GeneratedSQL(sql="", valid=False, explanation="still failing")
    )

    result = await loop.run(
        question="test",
        sql="SELECT * FROM bad_table",
        error_message="Table 'bad_table' doesn't exist",
        task_plan=SAMPLE_TASK_PLAN,
        schema_context=SAMPLE_SCHEMA,
        max_retries=3,
    )
    assert result.success is False
    assert len(result.attempts) == 3


@pytest.mark.asyncio
async def test_loop_other_stops_early():
    """'other' error type breaks the loop immediately."""
    loop = _make_loop(
        classifier_result=ErrorClassification("other", 0.5, "timeout"),
    )

    result = await loop.run(
        question="test",
        sql="SELECT 1",
        error_message="connection timeout",
        task_plan=SAMPLE_TASK_PLAN,
        schema_context=SAMPLE_SCHEMA,
        max_retries=3,
    )
    assert result.success is False
    assert len(result.attempts) == 1  # stopped after first classification


@pytest.mark.asyncio
async def test_loop_second_try_succeeds():
    """First attempt fails, second succeeds."""
    call_count = 0

    async def handler_fn(
        error_type: str, question: str, sql: str, error_message: str,
        task_plan: TaskPlan, schema_context: SchemaContext,
    ):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return GeneratedSQL(sql="", valid=False, explanation="still wrong")
        return GeneratedSQL(sql="SELECT * FROM orders", valid=True)

    loop = _make_loop(
        classifier_result=ErrorClassification("schema_error", 0.9, "schema"),
    )
    loop._apply_handler = handler_fn  # type: ignore[assignment]

    result = await loop.run(
        question="test",
        sql="SELECT * FROM bad_table",
        error_message="Table not found",
        task_plan=SAMPLE_TASK_PLAN,
        schema_context=SAMPLE_SCHEMA,
        max_retries=3,
    )
    assert result.success is True
    assert result.final_sql == "SELECT * FROM orders"
    assert len(result.attempts) == 2


# ── Handler tests ───────────────────────────────────────


@pytest.mark.asyncio
async def test_schema_error_handler_calls_retriever():
    """Schema error handler re-retrieves with broader top_k."""
    retriever = FakeRetriever(SAMPLE_SCHEMA)
    gen = FakeGenerator(GeneratedSQL(sql="SELECT 1", valid=True))
    loop = ReflectionLoop(
        api_key="test", model="test", base_url="http://fake",
        sql_generator=gen, schema_retriever=retriever,
    )

    result = await loop._handle_schema_error(
        "test", SAMPLE_TASK_PLAN, SAMPLE_SCHEMA,
    )
    assert result is not None
    assert result.valid is True


@pytest.mark.asyncio
async def test_syntax_error_handler_uses_llm():
    """Syntax error handler calls LLM to fix SQL."""
    loop = ReflectionLoop(
        api_key="test", model="test", base_url="http://fake",
        sql_generator=FakeGenerator(GeneratedSQL(sql="SELECT 1", valid=True)),
        schema_retriever=FakeRetriever(SAMPLE_SCHEMA),
    )
    loop._client.chat.completions.create = AsyncMock(
        return_value=_mock_llm(
            '{"sql": "SELECT id FROM orders", "explanation": "lowercase id", "valid": true}'
        )
    )

    result = await loop._handle_syntax_error(
        "SELECT ID FROM orders", "Unknown column 'ID'",
    )
    assert result is not None
    assert result.valid is True
    assert "id" in result.sql.lower()


@pytest.mark.asyncio
async def test_ambiguous_handler_reuses_generator():
    """Ambiguous handler re-generates with same generator."""
    gen = FakeGenerator(GeneratedSQL(sql="SELECT * FROM orders", valid=True))
    loop = ReflectionLoop(
        api_key="test", model="test", base_url="http://fake",
        sql_generator=gen, schema_retriever=FakeRetriever(SAMPLE_SCHEMA),
    )

    result = await loop._handle_ambiguous(
        "test", SAMPLE_TASK_PLAN, SAMPLE_SCHEMA,
    )
    assert result is not None
    assert result.valid is True
    assert "orders" in result.sql
