"""Tracing — TraceID generation and ``trace_node`` decorator for observability.

Usage:
    from app.core.tracing import new_trace_id, trace_node

    trace_id = new_trace_id()

    @trace_node("sql_generator", trace_id)
    async def generate(...):
        ...
"""

import time
import uuid
from functools import wraps
from typing import Any, Callable, Optional

from app.core.logging import logger


def new_trace_id() -> str:
    """Generate a unique trace ID (short hex string prefixed with ``tx_``)."""
    return f"tx_{uuid.uuid4().hex[:12]}"


def trace_node(
    node_name: str,
    trace_id: str,
    attempt: Optional[int] = None,
    parent_trace_id: Optional[str] = None,
) -> Callable:
    """Decorator that logs node start / end with timing.

    Usage:
        @trace_node("sql_generator", trace_id)
        async def generate(...):
            ...

    The decorated function's return value is passed through unchanged.
    If the function raises, the exception is logged and re-raised.
    """
    def decorator(fn: Callable) -> Callable:
        @wraps(fn)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            log_data = {
                "trace_id": trace_id,
                "node": node_name,
                "event": "node_start",
            }
            if attempt is not None:
                log_data["attempt"] = attempt
            if parent_trace_id is not None:
                log_data["parent_trace_id"] = parent_trace_id

            logger.info(log_data)

            start = time.perf_counter()
            try:
                result = await fn(*args, **kwargs)
                elapsed_ms = (time.perf_counter() - start) * 1000
                logger.info({
                    "trace_id": trace_id,
                    "node": node_name,
                    "event": "node_end",
                    "elapsed_ms": round(elapsed_ms, 2),
                    "success": True,
                    **( {} if attempt is None else {"attempt": attempt} ),
                    **( {} if parent_trace_id is None else {"parent_trace_id": parent_trace_id} ),
                })
                return result
            except Exception as exc:
                elapsed_ms = (time.perf_counter() - start) * 1000
                logger.error({
                    "trace_id": trace_id,
                    "node": node_name,
                    "event": "node_end",
                    "elapsed_ms": round(elapsed_ms, 2),
                    "success": False,
                    "error": str(exc),
                    **( {} if attempt is None else {"attempt": attempt} ),
                    **( {} if parent_trace_id is None else {"parent_trace_id": parent_trace_id} ),
                })
                raise

        return async_wrapper
    return decorator
