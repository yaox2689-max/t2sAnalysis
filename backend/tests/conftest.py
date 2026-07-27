"""pytest configuration — session-scoped event loop for Windows compat + shared fixtures."""

import asyncio
from unittest.mock import MagicMock

import pytest


@pytest.fixture(scope="session")
def event_loop():
    """Use a single event loop across all tests.

    Required on Windows where aiomysql / redis.asyncio connection
    pools break when the event loop is closed and recreated between
    individual test functions.
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    loop.close()


# ── Shared LLM response helpers ───────────────────────────


def mock_llm_response(content: str) -> MagicMock:
    """Create a mock OpenAI chat completion response.

    Args:
        content: The text content to return from the LLM.

    Returns:
        A MagicMock that mimics an OpenAI ChatCompletion response.
    """
    msg = MagicMock()
    msg.content = content
    choice = MagicMock()
    choice.message = msg
    resp = MagicMock()
    resp.choices = [choice]
    return resp


@pytest.fixture
def mock_llm_response_factory():
    """Provide mock_llm_response as a fixture for convenience."""
    return mock_llm_response


# ── Sample SchemaContext fixture ──────────────────────────


@pytest.fixture
def sample_schema():
    """A sample SchemaContext for tests."""
    from app.models.task import SchemaContext

    return SchemaContext(
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
        relationships=["orders.customer_id -> customers.id"],
    )
