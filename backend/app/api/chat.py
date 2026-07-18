"""Chat API — user question in, structured answer out.

Calls the LangGraph Workflow, then runs Chart and Insight tools
on the query result, and returns everything in a single response.
"""

import time
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.core.deps import app_ctx

router = APIRouter(prefix="/api", tags=["chat"])


# ── Request / Response models ──────────────────────────


class Message(BaseModel):
    role: str  # "user" | "assistant"
    content: str


class ChatRequest(BaseModel):
    question: str
    history: Optional[list[Message]] = None


class ChatResponse(BaseModel):
    sql: str = ""
    columns: list[str] = []
    rows: list[dict] = []
    chart_type: str = ""
    echarts_option: dict = {}
    insight: str = ""
    elapsed_ms: float = 0.0
    error: Optional[str] = None


# ── Route ──────────────────────────────────────────────


@router.post("/chat")
async def chat(request: ChatRequest) -> ChatResponse:
    """Receive a business question → run the agent → return structured answer."""
    ctx = await app_ctx.ensure_initialized()
    if ctx is None:
        raise HTTPException(status_code=503, detail="System not initialized")

    start = time.perf_counter()

    # 1. Run the LangGraph Workflow
    try:
        state = await ctx.graph.ainvoke({
            "question": request.question,
            "history": [m.dict() for m in request.history] if request.history else [],
            "retry_count": 0,
            "max_retries": 3,
            "errors": [],
        })
    except Exception as exc:
        elapsed_ms = (time.perf_counter() - start) * 1000
        return ChatResponse(
            error=f"Workflow error: {exc}",
            elapsed_ms=round(elapsed_ms, 2),
        )

    elapsed_ms = (time.perf_counter() - start) * 1000

    # 2. Extract results
    generated_sql = state.get("generated_sql")
    sql = generated_sql.sql if generated_sql else ""

    query_result = state.get("query_result")
    columns = query_result.columns if query_result else []
    rows = query_result.rows if query_result else []

    if not rows and not sql:
        return ChatResponse(
            sql=sql,
            columns=columns,
            rows=rows,
            elapsed_ms=round(elapsed_ms, 2),
            error="No data returned",
        )

    # 3. Run Chart Tool
    task_plan = state.get("task_plan")
    chart_option = None
    chart_type = ""
    if ctx.chart_tool:
        chart_result = ctx.chart_tool.render(query_result, task_plan)
        chart_type = chart_result.chart_type
        chart_option = chart_result.echarts_option

    # 4. Run Insight Tool
    insight_text = ""
    if ctx.insight_tool:
        try:
            insight_result = await ctx.insight_tool.summarize(
                query_result, request.question, chart_type=chart_type,
            )
            insight_text = insight_result.summary
        except Exception:
            insight_text = ""

    return ChatResponse(
        sql=sql,
        columns=columns,
        rows=rows,
        chart_type=chart_type,
        echarts_option=chart_option or {},
        insight=insight_text,
        elapsed_ms=round(elapsed_ms, 2),
    )
