"""Task Analyzer — parses a user question into a structured TaskPlan.

This is a pure LLM call with structured output parsing.
It does NOT involve Database, Agent, or multi-step reasoning.
"""

import json
from typing import Optional

import httpx
import openai

from app.core.prompt_loader import prompt_loader
from app.models.task import TaskPlan

_LLM_TIMEOUT = httpx.Timeout(60.0, connect=10.0)


class TaskAnalyzer:
    """Analyses a user question and produces a structured TaskPlan."""

    def __init__(
        self,
        api_key: str,
        model: str,
        base_url: Optional[str] = None,
        http_client: Optional[httpx.AsyncClient] = None,
    ) -> None:
        kwargs = {"api_key": api_key, "base_url": base_url, "timeout": _LLM_TIMEOUT}
        if http_client is not None:
            kwargs["http_client"] = http_client
        self.client = openai.AsyncOpenAI(**kwargs)
        self.model = model
        self._system_prompt = prompt_loader.load("sql_agent/task_analyzer")

    async def analyze(
        self,
        question: str,
        history: Optional[list[dict]] = None,
    ) -> TaskPlan:
        """Parse a user question into a TaskPlan using LLM."""
        messages = [
            {"role": "system", "content": self._system_prompt},
        ]

        if history:
            messages.extend(history)

        messages.append({"role": "user", "content": question})

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0.1,
        )

        raw = response.choices[0].message.content or ""

        return self._parse(raw)

    def _parse(self, raw: str) -> TaskPlan:
        """Parse LLM response into a TaskPlan.

        Falls back to unknown task_type on parse failure.
        """
        try:
            data = json.loads(raw)
            return TaskPlan(**data)
        except (json.JSONDecodeError, TypeError, ValueError):
            return TaskPlan(task_type="unknown")
