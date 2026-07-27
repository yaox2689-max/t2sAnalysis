"""Insight Tool — converts query results into natural-language business insights.

This is a single LLM summarizer call.  It does NOT:
- validate facts (that's Evidence Analyzer, PR #17)
- check SQL correctness
- access the database
- modify workflow state
- make tool calls

Usage:
    from app.tools.insight import InsightTool

    tool = InsightTool(api_key="...", model="deepseek-chat")
    result = await tool.summarize(query_result, "月销售额趋势")
"""

import json
from typing import Optional

from app.core.prompt_loader import prompt_loader
from app.core.utils import create_llm_client, format_query_result
from app.models.query import QueryResult


class InsightResult:
    """Output contract for the Insight Tool."""

    def __init__(
        self,
        summary: str = "",
        key_metrics: Optional[list[str]] = None,
        confidence: Optional[float] = None,
    ) -> None:
        self.summary = summary
        self.key_metrics = key_metrics or []
        self.confidence = confidence


def _load_prompt() -> str:
    return prompt_loader.load("tools/insight")


# ── Result formatting ───────────────────────────────────


def _format_result(result: QueryResult) -> str:
    """Format a QueryResult into a compact text summary for the LLM."""
    return format_query_result(result, lang="en")


# ── Tool ─────────────────────────────────────────────────


class InsightTool:
    """Generate natural-language business insights from query results."""

    def __init__(
        self,
        api_key: str,
        model: str,
        base_url: Optional[str] = None,
        http_client: Optional[object] = None,
    ) -> None:
        self._client = create_llm_client(api_key, base_url, http_client=http_client)
        self._model = model
        self._prompt = _load_prompt()

    async def summarize(
        self,
        result: QueryResult,
        question: str,
        chart_type: Optional[str] = None,
    ) -> InsightResult:
        """Summarize query results into 1-3 sentences of business insight.

        Returns early without an LLM call when there are no rows.
        """
        if not result.rows:
            return InsightResult(summary="数据不足，无法生成洞察")

        result_text = _format_result(result)

        user_parts = [f"## Question\n\n{question}", f"## Query Results\n\n{result_text}"]
        if chart_type:
            user_parts.append(f"## Chart Type\n\n{chart_type}")

        user_msg = "\n\n".join(user_parts)

        response = await self._client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": self._prompt},
                {"role": "user", "content": user_msg},
            ],
            temperature=0.3,
        )
        raw = response.choices[0].message.content or ""
        return self._parse(raw)

    @staticmethod
    def _parse(raw: str) -> InsightResult:
        """Parse LLM response into an InsightResult."""
        # Try extracting JSON from markdown code fence
        import re
        m = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', raw)
        if m:
            raw = m.group(1)
        try:
            data = json.loads(raw)
        except (json.JSONDecodeError, TypeError, ValueError):
            return InsightResult(summary=raw.strip(), confidence=0.0)

        return InsightResult(
            summary=data.get("summary", ""),
            key_metrics=data.get("key_metrics", []),
            confidence=data.get("confidence"),
        )
