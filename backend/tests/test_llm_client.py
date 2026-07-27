"""Tests for LLMClient and parse_llm_json utility."""

from __future__ import annotations

from typing import Optional
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.llm_client import LLMClient
from app.core.utils import parse_llm_json

# ── LLMClient tests ──────────────────────────────────────


@pytest.fixture
def mock_openai():
    """Mock AsyncOpenAI client."""
    client = AsyncMock()
    return client


@pytest.fixture
def llm_client(mock_openai):
    """Create an LLMClient with a mocked OpenAI client."""
    return LLMClient(client=mock_openai, model="test-model")


def _build_response(content: Optional[str]) -> MagicMock:
    """Build a mock OpenAI chat completion response."""
    msg = MagicMock()
    msg.content = content
    choice = MagicMock()
    choice.message = msg
    resp = MagicMock()
    resp.choices = [choice]
    return resp


class TestLLMClientCall:
    async def test_returns_content(self, llm_client, mock_openai):
        """call() returns the content string from the LLM response."""
        mock_openai.chat.completions.create.return_value = _build_response(
            "Hello, world!"
        )
        result = await llm_client.call(
            system_prompt="You are a helper.",
            user_msg="Say hello.",
        )
        assert result == "Hello, world!"

    async def test_passes_messages_through(self, llm_client, mock_openai):
        """call() with messages parameter uses them directly."""
        mock_openai.chat.completions.create.return_value = _build_response("ok")
        custom_messages = [
            {"role": "system", "content": "custom system"},
            {"role": "user", "content": "custom user"},
        ]
        await llm_client.call(
            system_prompt="ignored",
            user_msg="ignored",
            messages=custom_messages,
        )
        call_kwargs = mock_openai.chat.completions.create.call_args
        assert call_kwargs[1]["messages"] == custom_messages

    async def test_returns_empty_string_when_content_is_none(
        self, llm_client, mock_openai
    ):
        """call() returns empty string when content is None."""
        mock_openai.chat.completions.create.return_value = _build_response(None)
        result = await llm_client.call(
            system_prompt="system",
            user_msg="user",
        )
        assert result == ""

    async def test_constructs_system_and_user_messages(
        self, llm_client, mock_openai
    ):
        """Default behavior constructs [system, user] messages."""
        mock_openai.chat.completions.create.return_value = _build_response("ok")
        await llm_client.call(
            system_prompt="You are helpful.",
            user_msg="Help me.",
        )
        call_kwargs = mock_openai.chat.completions.create.call_args
        messages = call_kwargs[1]["messages"]
        assert messages[0]["role"] == "system"
        assert messages[0]["content"] == "You are helpful."
        assert messages[1]["role"] == "user"
        assert messages[1]["content"] == "Help me."


# ── parse_llm_json tests ─────────────────────────────────


class TestParseLLMJson:
    def test_valid_json_object(self):
        """Valid JSON object is parsed."""
        raw = '{"key": "value", "count": 42}'
        result = parse_llm_json(raw)
        assert result == {"key": "value", "count": 42}

    def test_valid_json_list(self):
        """Valid JSON list is parsed."""
        raw = '[{"name": "Alice"}, {"name": "Bob"}]'
        result = parse_llm_json(raw)
        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0]["name"] == "Alice"

    def test_json_in_markdown_fence(self):
        """JSON wrapped in markdown code fences is extracted."""
        raw = '''Here is the result:
```json
{"task_type": "query", "metrics": ["sales"]}
```
'''
        result = parse_llm_json(raw)
        assert result == {"task_type": "query", "metrics": ["sales"]}

    def test_json_in_plain_fence(self):
        """JSON in a plain ``` fence is also extracted."""
        raw = '''```
{"key": "value"}
```'''
        result = parse_llm_json(raw)
        assert result == {"key": "value"}

    def test_invalid_json_returns_none(self):
        """Invalid JSON returns None."""
        result = parse_llm_json("this is not json at all")
        assert result is None

    def test_empty_string_returns_none(self):
        """Empty string returns None."""
        result = parse_llm_json("")
        assert result is None

    def test_whitespace_only_returns_none(self):
        """Whitespace-only string returns None."""
        result = parse_llm_json("   \n\t  ")
        assert result is None

    def test_none_input_returns_none(self):
        """None input returns None."""
        result = parse_llm_json(None)  # type: ignore[arg-type]
        assert result is None

    def test_nested_json(self):
        """Nested JSON objects are parsed correctly."""
        raw = '{"data": {"items": [1, 2, 3]}}'
        result = parse_llm_json(raw)
        assert result["data"]["items"] == [1, 2, 3]
