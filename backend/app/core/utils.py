"""Shared utilities for sanitisation, LLM client, and result formatting."""

from __future__ import annotations

import httpx
from openai import AsyncOpenAI

from app.models.query import QueryResult

_PREVIEW_MAX_ROWS = 20


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
    http_client: object | None = None,
) -> AsyncOpenAI:
    """Create an ``AsyncOpenAI`` client with unified timeout settings."""
    kwargs: dict = {"api_key": api_key, "timeout": timeout}
    if base_url:
        kwargs["base_url"] = base_url
    if http_client is not None:
        kwargs["http_client"] = http_client
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
