"""Task Analyzer — parses a user question into a structured TaskPlan.

This is a pure LLM call with structured output parsing.
It does NOT involve Database, Agent, or multi-step reasoning.
"""

import json
from typing import Optional

from app.core.llm_client import LLMClient
from app.core.prompt_loader import prompt_loader
from app.models.task import TaskPlan


class TaskAnalyzer:
    """Analyses a user question and produces a structured TaskPlan."""

    def __init__(self, llm_client: LLMClient) -> None:
        self._llm_client = llm_client
        self._prompt = prompt_loader.load("sql_agent/task_analyzer")

    async def analyze(
        self,
        question: str,
        history: Optional[list[dict]] = None,
    ) -> TaskPlan:
        """Parse a user question into a TaskPlan using LLM."""
        messages: list[dict] = [
            {"role": "system", "content": self._prompt},
        ]

        if history:
            messages.extend(history)

        messages.append({"role": "user", "content": question})

        raw = await self._llm_client.call(
            system_prompt=self._prompt,
            user_msg=question,
            temperature=0.1,
            messages=messages,
        )

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
