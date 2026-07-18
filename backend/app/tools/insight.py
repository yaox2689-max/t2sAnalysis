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

from openai import AsyncOpenAI

from app.core.prompt_loader import prompt_loader
from app.models.query import QueryResult

_PREVIEW_MAX_ROWS = 20


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
    """Format a QueryResult into a compact text summary for the LLM.

    Includes:
    - Column names
    - Row count
    - Preview (first N rows)
    - Per-column statistics (min, max, avg, count)
    """
    lines: list[str] = []
    rows = result.rows or []
    columns = result.columns or []

    lines.append(f"Rows: {len(rows)}")
    lines.append(f"Columns: {', '.join(columns)}")

    # Preview
    if rows:
        lines.append("\nPreview:")
        preview = rows[:_PREVIEW_MAX_ROWS]
        for row in preview:
            vals = ", ".join(
                f"{k}={v}" for k, v in row.items() if k in columns
            )
            lines.append(f"  {vals}")

        if len(rows) > _PREVIEW_MAX_ROWS:
            lines.append(f"  ... and {len(rows) - _PREVIEW_MAX_ROWS} more rows")

    # Statistics per numeric column
    lines.append("\nStatistics:")
    for col in columns:
        vals: list[float] = []
        for r in rows:
            v = r.get(col)
            if v is not None:
                try:
                    vals.append(float(v))
                except (ValueError, TypeError):
                    pass
        if vals:
            lines.append(
                f"  {col}: count={len(vals)}, "
                f"min={min(vals):.2f}, max={max(vals):.2f}, "
                f"avg={sum(vals)/len(vals):.2f}"
            )
        else:
            # Non-numeric: show distinct count
            distinct = len({r.get(col) for r in rows if r.get(col) is not None})
            lines.append(f"  {col}: non-numeric, {distinct} distinct values")

    return "\n".join(lines)


# ── Tool ─────────────────────────────────────────────────


class InsightTool:
    """Generate natural-language business insights from query results."""

    def __init__(
        self,
        api_key: str,
        model: str,
        base_url: Optional[str] = None,
    ) -> None:
        self._client = AsyncOpenAI(api_key=api_key, base_url=base_url)
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
