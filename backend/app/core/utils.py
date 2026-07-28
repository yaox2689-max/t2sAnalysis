"""Shared utilities for sanitisation, LLM client, and result formatting."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

import httpx
from openai import AsyncOpenAI

if TYPE_CHECKING:
    from app.models.query import QueryResult

_PREVIEW_MAX_ROWS = 20


# ── Error handling ──────────────────────────────────────


def truncate_error(exc: Exception, limit: int = 200) -> str:
    """Return a truncated string representation of an exception.

    Args:
        exc: The exception to format.
        limit: Maximum number of characters to return.
    """
    return str(exc)[:limit]


# ── JSON parsing from LLM responses ─────────────────────


def parse_llm_json(raw: str, extract_from_fence: bool = True) -> dict | list | None:
    """Parse a JSON object/list from LLM response text.

    Args:
        raw: Raw text from LLM response.
        extract_from_fence: If True, first try to extract JSON from
            markdown code fences before parsing the whole string.

    Returns:
        Parsed JSON data, or ``None`` if parsing fails.
    """
    if not raw or not raw.strip():
        return None

    text = raw.strip()

    if extract_from_fence:
        match = re.search(r"```(?:json)?\s*\n?(.*?)\n?\s*```", text, re.DOTALL)
        if match:
            text = match.group(1).strip()

    try:
        import json

        return json.loads(text)
    except (json.JSONDecodeError, ValueError):
        return None


# ── NaN / Inf sanitisation ──────────────────────────────


def is_nan_or_inf(value: float) -> bool:
    """Return True if *value* is NaN or Inf."""
    return value != value or value == float("inf") or value == float("-inf")


def sanitize_float(value: object) -> object:
    """Replace NaN/Inf floats with ``None``; pass through everything else."""
    if isinstance(value, float) and is_nan_or_inf(value):
        return None
    return value


# ── LLM client factory ─────────────────────────────────

LLM_TIMEOUT = httpx.Timeout(60.0, connect=10.0)


def create_llm_client(
    api_key: str,
    base_url: str | None = None,
    timeout: httpx.Timeout = LLM_TIMEOUT,
    http_client: httpx.AsyncClient | None = None,
) -> AsyncOpenAI:
    """Create an ``AsyncOpenAI`` client with unified timeout settings.

    Creates a default httpx client that bypasses system proxy settings
    to avoid Windows proxy interference with LLM API calls.
    """
    if http_client is None:
        http_client = httpx.AsyncClient(proxy=None)
    kwargs: dict = {"api_key": api_key, "timeout": timeout, "http_client": http_client}
    if base_url:
        kwargs["base_url"] = base_url
    return AsyncOpenAI(**kwargs)


# ── Result formatting ───────────────────────────────────

_LABELS = {
    "en": {"rows": "Rows", "cols": "Columns", "preview": "Preview", "stats": "Statistics"},
    "zh": {"rows": "行数", "cols": "列", "preview": "预览", "stats": "统计"},
}


def format_query_result(
    result: QueryResult,
    label: str = "",
    lang: str = "en",
) -> str:
    """Format a QueryResult into a compact text summary for the LLM.

    Args:
        result: The query result to format.
        label: Optional prefix label (e.g. "primary", "comparison").
        lang: Language for labels — ``"en"`` (default) or ``"zh"``.
    """
    labels = _LABELS.get(lang, _LABELS["en"])
    prefix = f"[{label}] " if label else ""
    lines: list[str] = []
    rows = result.rows or []
    columns = result.columns or []

    lines.append(f"{prefix}{labels['rows']}: {len(rows)}, {labels['cols']}: {', '.join(columns)}")

    if rows:
        lines.append(f"{prefix}{labels['preview']}:")
        preview = rows[:_PREVIEW_MAX_ROWS]
        for row in preview:
            vals = ", ".join(f"{k}={v}" for k, v in row.items() if k in columns)
            lines.append(f"  {vals}")

        if len(rows) > _PREVIEW_MAX_ROWS:
            if lang == "zh":
                lines.append(f"  ... 共 {len(rows)} 行，以上仅展示前 {_PREVIEW_MAX_ROWS} 行")
            else:
                lines.append(f"  ... and {len(rows) - _PREVIEW_MAX_ROWS} more rows")

    lines.append(f"{prefix}{labels['stats']}:")
    if rows:
        for col in columns:
            numeric_vals: list[float] = []
            for r in rows:
                v = r.get(col)
                if v is not None:
                    try:
                        numeric_vals.append(float(v))
                    except (ValueError, TypeError):
                        pass
            if numeric_vals:
                if lang == "zh":
                    lines.append(
                        f"  {col}: 数量={len(numeric_vals)}, "
                        f"最小={min(numeric_vals):.2f}, "
                        f"最大={max(numeric_vals):.2f}, "
                        f"均值={sum(numeric_vals)/len(numeric_vals):.2f}"
                    )
                else:
                    lines.append(
                        f"  {col}: count={len(numeric_vals)}, "
                        f"min={min(numeric_vals):.2f}, max={max(numeric_vals):.2f}, "
                        f"avg={sum(numeric_vals)/len(numeric_vals):.2f}"
                    )
            else:
                distinct = len({r.get(col) for r in rows if r.get(col) is not None})
                if lang == "zh":
                    lines.append(f"  {col}: {distinct} 个不同值")
                else:
                    lines.append(f"  {col}: non-numeric, {distinct} distinct values")

    return "\n".join(lines)
