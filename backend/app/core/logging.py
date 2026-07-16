"""JSON-structured logger for the AI Data Analyst agent.

Usage:
    from app.core.logging import logger

    logger.info({"trace_id": "tx_...", "node": "analyze", "event": "node_start"})
"""

import json
import logging
import sys
from datetime import datetime, timezone

_FORMAT = "%(message)s"


class JSONFormatter(logging.Formatter):
    """Format log records as single-line JSON objects.

    Each record includes:
    - timestamp (ISO 8601, UTC)
    - level
    - plus whatever structured data is passed as *msg* (a dict).
    """

    def format(self, record: logging.LogRecord) -> str:
        data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
        }
        if isinstance(record.msg, dict):
            data.update(record.msg)
        else:
            data["message"] = str(record.msg)

        # Include exception info if present
        if record.exc_info and record.exc_info[1]:
            data["exception"] = str(record.exc_info[1])

        return json.dumps(data, ensure_ascii=False)


_handler = logging.StreamHandler(sys.stdout)
_handler.setFormatter(JSONFormatter())

logger = logging.getLogger("t2s_analysis")
logger.setLevel(logging.INFO)
logger.addHandler(_handler)
logger.propagate = False
