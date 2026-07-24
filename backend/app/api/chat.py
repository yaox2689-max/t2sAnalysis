"""Chat API — sessions, messages, and LangGraph Workflow integration.

Sessions and messages are persisted in MySQL so conversations survive
page refreshes and can be browsed from the History page.
"""

import json
import logging
import time
import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.core.config import settings
from app.core.database import Database
from app.core.deps import app_ctx
from app.core.tracing import new_trace_id

logger = logging.getLogger("t2s_analysis")


class _SafeEncoder(json.JSONEncoder):
    """Handle types that the default encoder cannot serialise (Decimal, date, …)."""

    def default(self, o: object) -> object:
        if isinstance(o, Decimal):
            return float(o)
        if isinstance(o, (datetime, date)):
            return o.isoformat()
        return super().default(o)

    def encode(self, o: object) -> str:
        return super().encode(self._sanitise(o))

    def _sanitise(self, o: object) -> object:
        """Recursively replace NaN / Inf with None (null in JSON)."""
        if isinstance(o, float):
            if o != o or o == float("inf") or o == float("-inf"):
                return None
            return o
        if isinstance(o, dict):
            return {k: self._sanitise(v) for k, v in o.items()}
        if isinstance(o, list):
            return [self._sanitise(v) for v in o]
        return o


def _convert_decimals(rows: list[dict]) -> list[dict]:
    """Convert Decimal values to float and NaN/Inf to None in a list of row dicts."""
    result = []
    for row in rows:
        clean = {}
        for k, v in row.items():
            if isinstance(v, Decimal):
                v = float(v)
            if isinstance(v, float) and (v != v or v == float("inf") or v == float("-inf")):
                v = None
            clean[k] = v
        result.append(clean)
    return result


def _get_db() -> Database:
    """Ensure database is initialised and return the global instance."""
    from app.core.database import db
    if not db.is_initialized:
        db.init()
    return db

router = APIRouter(prefix="/api", tags=["chat"])


# ── Request / Response models ──────────────────────────


class ChatRequest(BaseModel):
    question: str
    session_id: str

    class Config:
        json_schema_extra = {
            "properties": {
                "question": {"maxLength": 2000},
            }
        }


class ChatResponse(BaseModel):
    message_id: int = 0
    session_id: str = ""
    sql: str = ""
    columns: list[str] = []
    rows: list[dict] = []
    chart_type: str = ""
    echarts_option: dict = {}
    insight: str = ""
    elapsed_ms: float = 0.0
    error: Optional[str] = None


# ── Sessions ───────────────────────────────────────────


@router.post("/sessions")
async def create_session():
    """Create a new chat session."""
    db = _get_db()
    session_id = f"ses_{uuid.uuid4().hex[:12]}"
    await db.execute(
        "INSERT INTO sessions (id, title) VALUES (:id, :title)",
        {"id": session_id, "title": "新对话"},
    )
    return {"session_id": session_id}


@router.get("/sessions")
async def list_sessions():
    """List all sessions, newest first."""
    db = _get_db()
    rows = await db.execute(
        "SELECT id, title, created_at, updated_at FROM sessions ORDER BY updated_at DESC"
    )
    return {"sessions": rows}


@router.get("/sessions/{session_id}")
async def get_session(session_id: str):
    """Get all messages for a session."""
    db = _get_db()
    rows = await db.execute(
        "SELECT id, role, content, sql_text, chart_type, echarts_option, "
        "insight, `columns`, rows_data, elapsed_ms, created_at "
        "FROM messages WHERE session_id = :sid ORDER BY id ASC",
        {"sid": session_id},
    )
    for r in rows:
        for col in ("columns", "rows_data", "echarts_option"):
            if r.get(col) and isinstance(r[col], str):
                try:
                    r[col] = json.loads(r[col])
                except (json.JSONDecodeError, TypeError):
                    pass
    return {"messages": rows}


@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    """Delete a session and all its messages."""
    db = _get_db()
    await db.execute(
        "DELETE FROM messages WHERE session_id = :sid", {"sid": session_id}
    )
    await db.execute(
        "DELETE FROM sessions WHERE id = :sid", {"sid": session_id}
    )
    return {"ok": True}


# ── Chat ───────────────────────────────────────────────


@router.post("/chat")
async def chat(request: ChatRequest) -> ChatResponse:
    """Receive a business question → run the agent → return structured answer.

    Persists both the user question and the assistant response in the
    session's message history.
    """
    ctx = await app_ctx.ensure_initialized()

    # 1. Verify session exists and save user message
    db = _get_db()
    sess = await db.execute(
        "SELECT id FROM sessions WHERE id = :sid", {"sid": request.session_id}
    )
    if not sess:
        raise HTTPException(status_code=404, detail="Session not found")

    start = time.perf_counter()

    # 2. Run the LangGraph Workflow
    trace_id = new_trace_id()
    logger.info({"event": "chat_start", "trace_id": trace_id, "session_id": request.session_id})
    try:
        state = await ctx.graph.ainvoke({
            "question": request.question,
            "session_id": request.session_id,
            "trace_id": trace_id,
            "history": [],
            "retry_count": 0,
            "max_retries": 3,
            "errors": [],
        })
    except Exception as exc:
        elapsed_ms = (time.perf_counter() - start) * 1000
        logger.error({"event": "workflow_error", "error": str(exc), "session_id": request.session_id})
        await db.execute(
            "INSERT INTO messages (session_id, role, content, elapsed_ms) "
            "VALUES (:sid, 'user', :content, 0)",
            {"sid": request.session_id, "content": request.question},
        )
        await db.execute(
            "INSERT INTO messages (session_id, role, content, elapsed_ms) "
            "VALUES (:sid, 'assistant', :content, :elapsed)",
            {"sid": request.session_id, "content": "抱歉，处理您的问题时遇到了内部错误，请稍后重试。", "elapsed": round(elapsed_ms, 2)},
        )
        return ChatResponse(
            error="处理失败，请稍后重试",
            elapsed_ms=round(elapsed_ms, 2),
        )

    elapsed_ms = (time.perf_counter() - start) * 1000

    # 3. Extract results
    generated_sql = state.get("generated_sql")
    sql = generated_sql.sql if generated_sql else ""

    query_result = state.get("query_result")
    columns = query_result.columns if query_result else []
    rows = query_result.rows if query_result else []

    logger.info({
        "event": "workflow_result",
        "trace_id": trace_id,
        "has_sql": bool(sql),
        "has_result": query_result is not None,
        "columns": columns,
        "row_count": len(rows),
        "errors": state.get("errors", []),
    })

    if not rows and not sql:
        # Still save the user message even if no data
        await db.execute(
            "INSERT INTO messages (session_id, role, content, elapsed_ms) "
            "VALUES (:sid, 'user', :content, 0)",
            {"sid": request.session_id, "content": request.question},
        )
        return ChatResponse(
            session_id=request.session_id,
            sql=sql,
            columns=columns,
            rows=rows,
            elapsed_ms=round(elapsed_ms, 2),
            error="No data returned",
        )

    # 4. Run Chart Tool
    task_plan = state.get("task_plan")
    chart_option = None
    chart_type = ""
    if ctx.chart_tool and query_result:
        chart_result = ctx.chart_tool.render(query_result, task_plan)
        chart_type = chart_result.chart_type
        chart_option = chart_result.echarts_option

    # 5. Run Insight Tool
    insight_text = ""
    if ctx.insight_tool and query_result:
        try:
            insight_result = await ctx.insight_tool.summarize(
                query_result, request.question, chart_type=chart_type,
            )
            insight_text = insight_result.summary
        except Exception:
            insight_text = ""

    # 6. Save user message
    await db.execute(
        "INSERT INTO messages (session_id, role, content, elapsed_ms) "
        "VALUES (:sid, 'user', :content, 0)",
        {"sid": request.session_id, "content": request.question},
    )

    # 7. Save assistant message with all structured data
    msg_args = {
        "sid": request.session_id,
        "content": insight_text or "查询完成",
        "sql": sql,
        "chart_type": chart_type,
        "echarts": json.dumps(chart_option, ensure_ascii=False, cls=_SafeEncoder) if chart_option else None,
        "insight": insight_text,
        "columns": json.dumps(columns, ensure_ascii=False, cls=_SafeEncoder) if columns else None,
        "rows": json.dumps(rows, ensure_ascii=False, cls=_SafeEncoder) if rows else None,
        "elapsed": round(elapsed_ms, 2),
    }
    message_id = await db.execute_insert(
        "INSERT INTO messages (session_id, role, content, sql_text, chart_type, "
        "echarts_option, insight, `columns`, rows_data, elapsed_ms) "
        "VALUES (:sid, 'assistant', :content, :sql, :chart_type, "
        ":echarts, :insight, :columns, :rows, :elapsed)",
        msg_args,
    )

    # 8. Update session title (first message only)
    sess_check = await db.execute(
        "SELECT COUNT(*) AS cnt FROM messages WHERE session_id = :sid AND role = 'user'",
        {"sid": request.session_id},
    )
    if sess_check and sess_check[0]["cnt"] == 1:
        title = request.question[:60] + ("..." if len(request.question) > 60 else "")
        await db.execute(
            "UPDATE sessions SET title = :title WHERE id = :sid",
            {"title": title, "sid": request.session_id},
        )

    return ChatResponse(
        message_id=message_id,
        session_id=request.session_id,
        sql=sql,
        columns=columns,
        rows=_convert_decimals(rows),
        chart_type=chart_type,
        echarts_option=chart_option or {},
        insight=insight_text,
        elapsed_ms=round(elapsed_ms, 2),
    )
