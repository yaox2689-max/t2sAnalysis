"""DuckDB engine — the single analytics database.

Provides a synchronous DuckDB connection used by all analysis queries.
DuckDB is embedded (no server), columnar, and supports SQL directly
on CSV/Parquet files.

Usage:
    from app.core.duckdb import DuckDBEngine

    engine = DuckDBEngine()
    engine.init()
    result = engine.conn.execute("SELECT 1").fetchone()
"""

import logging
import os
from typing import Optional

logger = logging.getLogger("t2s_analysis")

# Default path: backend/data/analysis.duckdb
_DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data")


class DuckDBEngine:
    """Manages a single DuckDB connection for all analytics queries."""

    def __init__(self, db_path: Optional[str] = None) -> None:
        self._db_path = db_path or os.path.join(_DATA_DIR, "analysis.duckdb")
        self._conn: object = None  # duckdb.DuckDBPyConnection

    @property
    def conn(self):
        """The active DuckDB connection. Raises if not initialised."""
        if self._conn is None:
            raise RuntimeError("DuckDB not initialised — call engine.init() first")
        return self._conn

    @property
    def is_initialized(self) -> bool:
        return self._conn is not None

    def init(self) -> None:
        """Open (or create) the DuckDB database file."""
        if self._conn is not None:
            return

        import duckdb

        os.makedirs(os.path.dirname(self._db_path), exist_ok=True)
        self._conn = duckdb.connect(self._db_path)
        logger.info({"event": "duckdb_init", "path": self._db_path})

    def close(self) -> None:
        """Close the connection."""
        if self._conn is not None:
            self._conn.close()
            self._conn = None
            logger.info({"event": "duckdb_close"})

    def tables(self) -> list[str]:
        """List all tables in the database."""
        rows = self.conn.execute("SHOW TABLES").fetchall()
        return [r[0] for r in rows]

    def execute(self, sql: str) -> object:
        """Execute SQL and return the DuckDB result object.

        For SELECT queries, use .fetchdf() to get a DataFrame or
        .fetchall() to get rows. For DDL/DML, the result is informational.
        """
        return self.conn.execute(sql)


# Module-level singleton
duckdb_engine = DuckDBEngine()
