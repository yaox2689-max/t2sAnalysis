"""Tests for LangGraph Workflow — state, nodes, routers, and full graph."""
import pytest
from langgraph.graph import StateGraph

from app.agents.state import AgentState
from app.graph.graph import build_graph
from app.graph.nodes import (
    analyze_task_node,
    execute_sql_node,
    generate_sql_node,
    reflect_node,
    retrieve_schema_node,
    validate_sql_node,
)
from app.graph.routers import (
    route_after_execute,
    route_after_reflection,
    route_after_validate,
)
from app.models.query import QueryResult
from app.models.task import GeneratedSQL, SchemaContext, TaskPlan
from app.tools.sql_validator import ValidationResult


# ── Fixtures ─────────────────────────────────────────────

SAMPLE_PLAN = TaskPlan(task_type="aggregation", metrics=["total"], dimensions=["category"])
SAMPLE_SCHEMA = SchemaContext(
    tables=["orders"],
    columns={"orders": [{"column_name": "id", "data_type": "int"}]},
)
SAMPLE_SQL = GeneratedSQL(sql="SELECT * FROM orders", valid=True)
SAMPLE_RESULT = QueryResult(columns=["id"], rows=[{"id": 1}])

BASE_STATE: AgentState = {
    "question": "test",
    "history": [],
    "task_plan": SAMPLE_PLAN,
    "schema_context": SAMPLE_SCHEMA,
    "generated_sql": None,
    "validation_result": None,
    "query_result": None,
    "current_sql": None,
    "retry_count": 0,
    "max_retries": 3,
    "next_action": None,
    "errors": [],
}


async def _noop(*args, **kwargs):
    pass


class FakeAnalyzer:
    async def analyze(self, question, history=None):
        return SAMPLE_PLAN


class FakeRetriever:
    async def retrieve(self, question, **kwargs):
        return SAMPLE_SCHEMA


class FakeGenerator:
    async def generate(self, plan, schema):
        return SAMPLE_SQL


class FakeValidator:
    def validate(self, sql: str) -> ValidationResult:
        return ValidationResult(passed=True)


class FakeValidatorFails(FakeValidator):
    def validate(self, sql: str) -> ValidationResult:
        return ValidationResult(passed=False, risk_level="high", warnings=["PARSE_ERROR"])


class FakeExecutor:
    async def execute(self, sql: str):
        return SAMPLE_RESULT


class FakeExecutorFails(FakeExecutor):
    async def execute(self, sql: str):
        raise Exception("Table not found")


class FakeReflection:
    def __init__(self, next_action="stop"):
        self._next_action = next_action

    async def run(self, question, sql, error, plan, ctx, max_retries=3):
        from app.agents.reflection import ReflectionResult
        return ReflectionResult(
            success=False,
            final_sql="SELECT * FROM orders",
            next_action=self._next_action,
        )


# ── Router tests ─────────────────────────────────────────


class TestRouters:
    def test_route_after_validate_passed(self):
        s = {**BASE_STATE, "validation_result": ValidationResult(passed=True)}
        assert route_after_validate(s) == "execute"

    def test_route_after_validate_failed(self):
        s = {**BASE_STATE, "validation_result": ValidationResult(passed=False)}
        assert route_after_validate(s) == "reflect"

    def test_route_after_validate_none(self):
        s = {**BASE_STATE, "validation_result": None}
        assert route_after_validate(s) == "reflect"

    def test_route_after_execute_success(self):
        s = {**BASE_STATE, "query_result": SAMPLE_RESULT}
        assert route_after_execute(s) == "end"

    def test_route_after_execute_failure(self):
        s = {**BASE_STATE, "query_result": None, "retry_count": 1}
        assert route_after_execute(s) == "reflect"

    def test_route_after_execute_exhausted(self):
        s = {**BASE_STATE, "query_result": None, "retry_count": 3, "max_retries": 3}
        assert route_after_execute(s) == "end"

    def test_route_after_reflection_stop(self):
        s = {**BASE_STATE, "next_action": "stop", "retry_count": 1}
        assert route_after_reflection(s) == "end"

    def test_route_after_reflection_retry_generate(self):
        s = {**BASE_STATE, "next_action": "retry_generate", "retry_count": 1}
        assert route_after_reflection(s) == "generate"

    def test_route_after_reflection_retry_retrieve(self):
        s = {**BASE_STATE, "next_action": "retry_retrieve", "retry_count": 1}
        assert route_after_reflection(s) == "retrieve"

    def test_route_after_reflection_exhausted(self):
        s = {**BASE_STATE, "next_action": "retry_generate", "retry_count": 3, "max_retries": 3}
        assert route_after_reflection(s) == "end"


# ── Node tests ───────────────────────────────────────────


class TestNodes:
    async def test_analyze_task_node(self):
        result = await analyze_task_node(BASE_STATE, analyzer=FakeAnalyzer())
        assert result["task_plan"].task_type == "aggregation"

    async def test_retrieve_schema_node(self):
        result = await retrieve_schema_node(BASE_STATE, retriever=FakeRetriever())
        assert "orders" in result["schema_context"].tables

    async def test_generate_sql_node(self):
        s = {**BASE_STATE, "task_plan": SAMPLE_PLAN, "schema_context": SAMPLE_SCHEMA}
        result = await generate_sql_node(s, generator=FakeGenerator())
        assert result["generated_sql"].valid is True
        assert result["current_sql"] == "SELECT * FROM orders"

    async def test_validate_sql_node(self):
        s = {**BASE_STATE, "current_sql": "SELECT 1"}
        result = await validate_sql_node(s, validator=FakeValidator())
        assert result["validation_result"].passed is True

    async def test_execute_sql_node_success(self):
        s = {**BASE_STATE, "current_sql": "SELECT 1"}
        result = await execute_sql_node(s, executor=FakeExecutor())
        assert result["query_result"] is not None
        assert result["query_result"].columns == ["id"]

    async def test_execute_sql_node_failure(self):
        s = {**BASE_STATE, "current_sql": "SELECT 1"}
        result = await execute_sql_node(s, executor=FakeExecutorFails())
        assert result["query_result"] is None
        assert "Table not found" in result["errors"][0]

    async def test_reflect_node_sets_next_action(self):
        s = {**BASE_STATE, "current_sql": "SELECT * FROM bad_table", "errors": ["Table not found"]}
        result = await reflect_node(s, reflection=FakeReflection(next_action="retry_retrieve"))
        assert result["next_action"] == "retry_retrieve"
        assert result["retry_count"] == 1
        assert result["current_sql"] == "SELECT * FROM orders"


# ── Full graph tests ─────────────────────────────────────


@pytest.fixture
def graph():
    return build_graph(
        analyzer=FakeAnalyzer(),
        retriever=FakeRetriever(),
        generator=FakeGenerator(),
        validator=FakeValidator(),
        executor=FakeExecutor(),
        reflection=FakeReflection(),
    )


@pytest.mark.asyncio
async def test_graph_happy_path(graph):
    """All nodes pass → graph produces a query result."""
    result = await graph.ainvoke({
        "question": "test",
        "history": [],
        "max_retries": 3,
        "retry_count": 0,
        "errors": [],
    })
    assert result["task_plan"].task_type == "aggregation"
    assert result["schema_context"] is not None
    assert result["generated_sql"].valid is True
    assert result["validation_result"].passed is True
    assert result["query_result"] is not None
    assert result["query_result"].columns == ["id"]


@pytest.mark.asyncio
async def test_graph_validation_failure_leads_to_reflection():
    """Validator fails → reflection node runs."""
    g = build_graph(
        analyzer=FakeAnalyzer(),
        retriever=FakeRetriever(),
        generator=FakeGenerator(),
        validator=FakeValidatorFails(),
        executor=FakeExecutor(),
        reflection=FakeReflection(next_action="stop"),
    )
    result = await g.ainvoke({
        "question": "test",
        "history": [],
        "max_retries": 3,
        "retry_count": 0,
        "errors": [],
    })
    assert result["validation_result"].passed is False
    # reflection ran — next_action was set
    assert result.get("next_action") is not None


@pytest.mark.asyncio
async def test_graph_execution_failure_leads_to_reflection():
    """Executor fails → reflection node runs."""
    g = build_graph(
        analyzer=FakeAnalyzer(),
        retriever=FakeRetriever(),
        generator=FakeGenerator(),
        validator=FakeValidator(),
        executor=FakeExecutorFails(),
        reflection=FakeReflection(next_action="stop"),
    )
    result = await g.ainvoke({
        "question": "test",
        "history": [],
        "max_retries": 3,
        "retry_count": 0,
        "errors": [],
    })
    assert result["query_result"] is None
    assert result.get("next_action") is not None


@pytest.mark.asyncio
async def test_graph_retry_retrieve_reruns_retrieve_and_generate():
    """reflection next_action=retry_retrieve → retrieve → generate → validate → execute."""
    g = build_graph(
        analyzer=FakeAnalyzer(),
        retriever=FakeRetriever(),
        generator=FakeGenerator(),
        validator=FakeValidator(),
        executor=FakeExecutor(),
        reflection=FakeReflection(next_action="retry_retrieve"),
    )
    result = await g.ainvoke({
        "question": "test",
        "history": [],
        "retry_count": 0,
        "max_retries": 3,
        "errors": ["Table not found"],
        "current_sql": "SELECT * FROM bad_table",
    })
    # After retry_retrieve → retrieve → generate → validate → execute → success
    assert result["query_result"] is not None
