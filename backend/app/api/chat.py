"""Chat API — sessions, messages, and LangGraph Workflow integration.

Sessions and messages are persisted in MySQL so conversations survive
page refreshes and can be browsed from the History page.
"""

import json
import logging
import time
import uuid
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.core.auth import get_current_user
from app.core.config import settings
from app.core.database import db
from app.core.deps import app_ctx
from app.core.tracing import new_trace_id
from app.core.utils import sanitize_float, truncate_error
from app.services.auth_service import UserOut
from app.services.chat_service import (
    _SafeEncoder,
    persist_conversation,
    run_post_workflow_tools,
)
from main import limiter

logger = logging.getLogger("t2s_analysis")


def _convert_decimals(rows: list[dict]) -> list[dict]:
    """Convert Decimal values to float and NaN/Inf to None in a list of row dicts."""
    result = []
    for row in rows:
        clean = {}
        for k, v in row.items():
            if isinstance(v, Decimal):
                v = float(v)
            v = sanitize_float(v)
            clean[k] = v
        result.append(clean)
    return result


async def _verify_session(session_id: str, user_id: str) -> None:
    """Verify session ownership, raise 404 if not found."""
    sess = await db.execute(
        "SELECT id FROM sessions WHERE id = :sid AND user_id = :uid",
        {"sid": session_id, "uid": user_id},
    )
    if not sess:
        raise HTTPException(status_code=404, detail="Session not found")


async def _load_history(session_id: str) -> list[dict]:
    """Load last 20 messages for conversation context."""
    history_rows = await db.execute(
        "SELECT role, content FROM messages "
        "WHERE session_id = :sid AND role IN ('user', 'assistant') "
        "ORDER BY id DESC LIMIT 20",
        {"sid": session_id},
    )
    history_rows.reverse()
    return [{"role": r["role"], "content": r["content"]} for r in history_rows]


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
    evidence: Optional[dict] = None
    elapsed_ms: float = 0.0
    error: Optional[str] = None


# ── Sessions ───────────────────────────────────────────


@router.post("/sessions")
async def create_session(user: UserOut = Depends(get_current_user)):
    """Create a new chat session."""
    from app.bootstrap import bootstrap
    await bootstrap.run()
    session_id = f"ses_{uuid.uuid4().hex[:12]}"
    await db.execute(
        "INSERT INTO sessions (id, title, user_id) VALUES (:id, :title, :uid)",
        {"id": session_id, "title": "新对话", "uid": user.id},
    )
    return {"session_id": session_id}


@router.get("/sessions")
async def list_sessions(user: UserOut = Depends(get_current_user)):
    """List all sessions for the current user, newest first."""
    from app.bootstrap import bootstrap
    await bootstrap.run()
    rows = await db.execute(
        "SELECT id, title, created_at, updated_at FROM sessions "
        "WHERE user_id = :uid ORDER BY updated_at DESC",
        {"uid": user.id},
    )
    return {"sessions": rows}


@router.get("/sessions/{session_id}")
async def get_session(session_id: str, user: UserOut = Depends(get_current_user)):
    """Get all messages for a session (owned by current user)."""
    from app.bootstrap import bootstrap
    await bootstrap.run()
    await _verify_session(session_id, user.id)
    rows = await db.execute(
        "SELECT id, role, content, sql_text, chart_type, echarts_option, "
        "insight, `columns`, rows_data, evidence, elapsed_ms, created_at "
        "FROM messages WHERE session_id = :sid ORDER BY id ASC",
        {"sid": session_id},
    )
    for r in rows:
        for col in ("columns", "rows_data", "echarts_option", "evidence"):
            if r.get(col) and isinstance(r[col], str):
                try:
                    r[col] = json.loads(r[col])
                except (json.JSONDecodeError, TypeError):
                    pass
    return {"messages": rows}


@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str, user: UserOut = Depends(get_current_user)):
    """Delete a session and all its messages (owned by current user)."""
    from app.bootstrap import bootstrap
    await bootstrap.run()
    await _verify_session(session_id, user.id)
    await db.execute(
        "DELETE FROM messages WHERE session_id = :sid", {"sid": session_id}
    )
    await db.execute(
        "DELETE FROM sessions WHERE id = :sid", {"sid": session_id}
    )
    return {"ok": True}


# ── Chat ───────────────────────────────────────────────


@router.post("/chat")
@limiter.limit(settings.RATE_LIMIT_CHAT)
async def chat(request: Request, req: ChatRequest, user: UserOut = Depends(get_current_user)) -> ChatResponse:
    """Receive a business question → run the agent → return structured answer.

    Persists both the user question and the assistant response in the
    session's message history.
    """
    ctx = await app_ctx.ensure_initialized()

    # 1. Verify session exists and belongs to user
    from app.bootstrap import bootstrap
    await bootstrap.run()
    await _verify_session(req.session_id, user.id)

    # 2. Load recent conversation history for multi-turn context
    history = await _load_history(req.session_id)

    start = time.perf_counter()

    # 3. Run the LangGraph Workflow
    trace_id = new_trace_id()
    logger.info({"event": "chat_start", "trace_id": trace_id, "session_id": req.session_id})
    try:
        state = await ctx.graph.ainvoke({
            "question": req.question,
            "session_id": req.session_id,
            "user_id": user.id,
            "trace_id": trace_id,
            "history": history,
            "retry_count": 0,
            "max_retries": 3,
            "errors": [],
        })
    except Exception as exc:
        elapsed_ms = (time.perf_counter() - start) * 1000
        logger.error({"event": "workflow_error", "error": truncate_error(exc), "session_id": req.session_id})
        await db.execute(
            "INSERT INTO messages (session_id, role, content, elapsed_ms) "
            "VALUES (:sid, 'user', :content, 0)",
            {"sid": req.session_id, "content": req.question},
        )
        await db.execute(
            "INSERT INTO messages (session_id, role, content, elapsed_ms) "
            "VALUES (:sid, 'assistant', :content, :elapsed)",
            {"sid": req.session_id, "content": "抱歉，处理您的问题时遇到了内部错误，请稍后重试。", "elapsed": round(elapsed_ms, 2)},
        )
        return ChatResponse(
            error="处理失败，请稍后重试",
            elapsed_ms=round(elapsed_ms, 2),
        )

    elapsed_ms = (time.perf_counter() - start) * 1000

    # 4. Extract results
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
            {"sid": req.session_id, "content": req.question},
        )
        return ChatResponse(
            session_id=req.session_id,
            sql=sql,
            columns=columns,
            rows=rows,
            elapsed_ms=round(elapsed_ms, 2),
            error="No data returned",
        )

    # 5. Run Chart Tool
    task_plan = state.get("task_plan")
    chart_type, chart_option, insight_text, evidence_data = await run_post_workflow_tools(
        ctx, query_result, req.question, task_plan,
    )

    # 6. Save messages and update session title
    result_dict = {
        "sql": sql,
        "chart_type": chart_type,
        "echarts_option": chart_option,
        "insight": insight_text,
        "columns": columns,
        "rows": rows,
        "evidence": evidence_data,
        "elapsed_ms": elapsed_ms,
    }
    message_id = await persist_conversation(
        session_id=req.session_id,
        user_id=user.id,
        question=req.question,
        result=result_dict,
        history=history,
    )

    return ChatResponse(
        message_id=message_id,
        session_id=req.session_id,
        sql=sql,
        columns=columns,
        rows=_convert_decimals(rows),
        chart_type=chart_type,
        echarts_option=chart_option or {},
        insight=insight_text,
        evidence=evidence_data,
        elapsed_ms=round(elapsed_ms, 2),
    )


# ── SSE Streaming ─────────────────────────────────────

# Node display names for progress events
_NODE_LABELS: dict[str, str] = {
    "analyze": "分析任务",
    "retrieve": "检索数据结构",
    "generate": "生成SQL",
    "validate": "校验SQL",
    "execute": "执行查询",
    "reflect": "反思优化",
}


@router.post("/chat/stream")
@limiter.limit(settings.RATE_LIMIT_CHAT)
async def chat_stream(request: Request, req: ChatRequest, user: UserOut = Depends(get_current_user)):
    """SSE endpoint that streams progress events during workflow execution."""
    ctx = await app_ctx.ensure_initialized()
    from app.bootstrap import bootstrap
    await bootstrap.run()

    await _verify_session(req.session_id, user.id)

    # Load conversation history
    history = await _load_history(req.session_id)

    async def event_generator():
        trace_id = new_trace_id()
        start = time.perf_counter()
        logger.info({"event": "chat_stream_start", "trace_id": trace_id, "session_id": req.session_id})

        initial_state = {
            "question": req.question,
            "session_id": req.session_id,
            "user_id": user.id,
            "trace_id": trace_id,
            "history": history,
            "retry_count": 0,
            "max_retries": 3,
            "errors": [],
        }

        final_state = None
        try:
            async for event in ctx.graph.astream(initial_state, stream_mode="updates"):
                for node_name, update in event.items():
                    label = _NODE_LABELS.get(node_name, node_name)
                    progress = {"type": "progress", "node": node_name, "label": label}
                    if node_name == "analyze" and update.get("task_plan"):
                        progress["task_type"] = update["task_plan"].task_type
                    elif node_name == "execute":
                        qr = update.get("query_result")
                        progress["row_count"] = qr.row_count if qr else 0
                    yield f"data: {json.dumps(progress, ensure_ascii=False, cls=_SafeEncoder)}\n\n"

                    if final_state is None:
                        final_state = dict(initial_state)
                    final_state.update(update)
        except Exception as exc:
            elapsed_ms = (time.perf_counter() - start) * 1000
            logger.error({"event": "chat_stream_error", "error": truncate_error(exc)})
            yield f'data: {json.dumps({"type": "error", "message": "处理失败，请稍后重试"}, ensure_ascii=False)}\n\n'
            return

        elapsed_ms = (time.perf_counter() - start) * 1000

        if not final_state:
            yield f'data: {json.dumps({"type": "error", "message": "处理失败"}, ensure_ascii=False)}\n\n'
            return

        # Extract results
        generated_sql = final_state.get("generated_sql")
        sql = generated_sql.sql if generated_sql else ""
        query_result = final_state.get("query_result")
        columns = query_result.columns if query_result else []
        rows = query_result.rows if query_result else []

        if not rows and not sql:
            await db.execute(
                "INSERT INTO messages (session_id, role, content, elapsed_ms) "
                "VALUES (:sid, 'user', :content, 0)",
                {"sid": req.session_id, "content": req.question},
            )
            yield f'data: {json.dumps({"type": "error", "message": "No data returned", "elapsed_ms": round(elapsed_ms, 2)}, ensure_ascii=False, cls=_SafeEncoder)}\n\n'
            return

        # Post-workflow tools
        task_plan = final_state.get("task_plan")
        chart_type, chart_option, insight_text, evidence_data = await run_post_workflow_tools(
            ctx, query_result, req.question, task_plan,
        )

        # Save messages and update session title
        result_dict = {
            "sql": sql,
            "chart_type": chart_type,
            "echarts_option": chart_option,
            "insight": insight_text,
            "columns": columns,
            "rows": rows,
            "evidence": evidence_data,
            "elapsed_ms": elapsed_ms,
        }
        message_id = await persist_conversation(
            session_id=req.session_id,
            user_id=user.id,
            question=req.question,
            result=result_dict,
            history=history,
        )

        # Yield final result
        result_payload = {
            "type": "result",
            "message_id": message_id,
            "session_id": req.session_id,
            "sql": sql,
            "columns": columns,
            "rows": _convert_decimals(rows),
            "chart_type": chart_type,
            "echarts_option": chart_option or {},
            "insight": insight_text,
            "evidence": evidence_data,
            "elapsed_ms": round(elapsed_ms, 2),
        }
        yield f"data: {json.dumps(result_payload, ensure_ascii=False, cls=_SafeEncoder)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
