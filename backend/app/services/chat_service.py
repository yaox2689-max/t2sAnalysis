"""Chat service — shared business logic for chat endpoints.

Extracts the post-workflow processing (chart, insight, evidence),
message persistence, and session title management that was duplicated
between the streaming and non-streaming chat endpoints.
"""

import json
import logging
from typing import Any, Optional

from app.core.database import Database

logger = logging.getLogger("t2s_analysis")


async def run_post_workflow_tools(
    ctx: Any,
    query_result: Any,
    question: str,
    task_plan: Any = None,
) -> tuple[str, str, Optional[dict], Optional[dict]]:
    """Run chart, insight, and evidence tools after workflow execution.

    Returns:
        (chart_type, chart_option_json_str, insight_text, evidence_data)
    """
    chart_option = None
    chart_type = ""
    if ctx.chart_tool and query_result:
        chart_result = ctx.chart_tool.render(query_result, task_plan)
        chart_type = chart_result.chart_type
        chart_option = chart_result.echarts_option

    insight_text = ""
    if ctx.insight_tool and query_result:
        try:
            insight_result = await ctx.insight_tool.summarize(
                query_result, question, chart_type=chart_type,
            )
            insight_text = insight_result.summary
        except Exception as exc:
            logger.warning({"event": "insight_failed", "error": str(exc)[:200]})

    evidence_data = None
    if ctx.evidence_analyzer and query_result:
        try:
            evidence_report = await ctx.evidence_analyzer.analyze(
                question, query_result,
            )
            evidence_data = {
                "conclusion": evidence_report.conclusion,
                "evidence_chain": [
                    {"claim": e.claim, "data": e.data, "source": e.source, "strength": e.strength}
                    for e in evidence_report.evidence_chain
                ],
                "suggestions": evidence_report.suggestions,
                "limitations": evidence_report.limitations,
            }
        except Exception as exc:
            logger.warning({"event": "evidence_failed", "error": str(exc)[:200]})

    return chart_type, chart_option, insight_text, evidence_data


async def save_user_message(db: Database, session_id: str, question: str) -> None:
    """Persist the user's question as a message."""
    await db.execute(
        "INSERT INTO messages (session_id, role, content, elapsed_ms) "
        "VALUES (:sid, 'user', :content, 0)",
        {"sid": session_id, "content": question},
    )


async def save_assistant_message(
    db: Database,
    session_id: str,
    sql: str,
    chart_type: str,
    chart_option: Any,
    insight_text: str,
    columns: list,
    rows: list,
    evidence_data: Optional[dict],
    elapsed_ms: float,
    safe_encoder: type,
) -> int:
    """Persist the assistant's structured response and return the message ID."""
    content = insight_text or "查询完成"
    msg_args = {
        "sid": session_id,
        "content": content,
        "sql": sql,
        "chart_type": chart_type,
        "echarts": json.dumps(chart_option, ensure_ascii=False, cls=safe_encoder) if chart_option else None,
        "insight": insight_text,
        "columns": json.dumps(columns, ensure_ascii=False, cls=safe_encoder) if columns else None,
        "rows": json.dumps(rows, ensure_ascii=False, cls=safe_encoder) if rows else None,
        "evidence": json.dumps(evidence_data, ensure_ascii=False, cls=safe_encoder) if evidence_data else None,
        "elapsed": round(elapsed_ms, 2),
    }
    return await db.execute_insert(
        "INSERT INTO messages (session_id, role, content, sql_text, chart_type, "
        "echarts_option, insight, `columns`, rows_data, evidence, elapsed_ms) "
        "VALUES (:sid, 'assistant', :content, :sql, :chart_type, "
        ":echarts, :insight, :columns, :rows, :evidence, :elapsed)",
        msg_args,
    )


async def update_session_title_if_first(
    db: Database, session_id: str, question: str
) -> None:
    """Update session title to the question text if this is the first user message."""
    sess_check = await db.execute(
        "SELECT COUNT(*) AS cnt FROM messages WHERE session_id = :sid AND role = 'user'",
        {"sid": session_id},
    )
    if sess_check and sess_check[0]["cnt"] == 1:
        title = question[:60] + ("..." if len(question) > 60 else "")
        await db.execute(
            "UPDATE sessions SET title = :title WHERE id = :sid",
            {"title": title, "sid": session_id},
        )
