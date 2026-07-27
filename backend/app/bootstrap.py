"""Bootstrap — system startup initialization.

Run once on application start:
1. Open DuckDB connection
2. Create MySQL tables (fallback) — schema migrations via ``alembic upgrade head``
3. Initialize DatasetRegistry
4. Initialize PromptBuilder

Usage:
    from app.bootstrap import bootstrap

    await bootstrap.run()
"""

import asyncio
import logging
import os

from app.core.config import settings
from app.core.database import Database
from app.core.duckdb import DuckDBEngine
from app.core.utils import truncate_error

logger = logging.getLogger("t2s_analysis")


class Bootstrap:
    """System startup orchestrator."""

    def __init__(self) -> None:
        self._initialized = False
        self.profiler = None
        self.registry = None
        self.prompt_builder = None
        self.executor = None
        self.dataset_manager = None

    @property
    def is_initialized(self) -> bool:
        """Return True if bootstrap has completed."""
        return self._initialized

    async def run(self) -> None:
        """Full startup sequence."""
        if self._initialized:
            return

        logger.info({"event": "bootstrap_start"})

        # 1. Init DuckDB
        from app.core.duckdb import duckdb_engine
        duckdb_engine.init()
        logger.info({"event": "bootstrap_duckdb_ready"})

        # 2. Init MySQL (business metadata) — CREATE TABLE IF NOT EXISTS as fallback
        #    For schema migrations, run: alembic upgrade head
        from app.core.database import db
        db.init()
        await self._ensure_users_table(db)
        await self._ensure_datasets_table(db)
        await self._ensure_chat_tables(db)

        # 3. Init SchemaProfiler
        from app.tools.schema_profiler import SchemaProfiler
        self.profiler = SchemaProfiler(duckdb_engine)

        # 4. Init DatasetRegistry + load from MySQL
        from app.services.dataset_registry import DatasetRegistry
        self.registry = DatasetRegistry(duckdb_engine, self.profiler)
        await self._load_datasets_from_mysql(db, duckdb_engine)

        # 5. Init PromptBuilder (with DuckDB engine for sample rows)
        from app.services.prompt_builder import PromptBuilder
        self.prompt_builder = PromptBuilder(duckdb_engine=duckdb_engine)

        # 6. Init DuckDBExecutor
        from app.tools.duckdb_executor import DuckDBExecutor
        self.executor = DuckDBExecutor(duckdb_engine, timeout=settings.SQL_TIMEOUT)

        # 7. Init DatasetManager
        from app.services.dataset_manager import DatasetManager
        self.dataset_manager = DatasetManager(duckdb_engine, db, self.registry, self.profiler)

        # 8. Log final state
        tables = await asyncio.to_thread(duckdb_engine.tables)
        logger.info({"event": "bootstrap_complete", "tables": tables})

        self._initialized = True

    async def _ensure_users_table(self, db: Database) -> None:
        """Create users table in MySQL if it doesn't exist."""
        users_ddl = (
            "CREATE TABLE IF NOT EXISTS users ("
            "  id VARCHAR(36) PRIMARY KEY,"
            "  username VARCHAR(64) NOT NULL UNIQUE,"
            "  password_hash VARCHAR(255) NOT NULL,"
            "  display_name VARCHAR(128),"
            "  created_at DATETIME DEFAULT CURRENT_TIMESTAMP"
            ")"
        )
        try:
            await db.execute(users_ddl)
            logger.info({"event": "users_table_ready"})
        except Exception as exc:
            logger.warning({"event": "users_table_exists", "detail": truncate_error(exc, 100)})

    async def _ensure_datasets_table(self, db: Database) -> None:
        """Create datasets table in MySQL if it doesn't exist.

        Schema migrations should be managed via Alembic:
            alembic upgrade head
        """
        sql_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "..", "scripts", "schema_datasets.sql"
        )
        if os.path.exists(sql_path):
            with open(sql_path, "r", encoding="utf-8") as f:
                ddl = f.read()
            try:
                await db.execute(ddl)
                logger.info({"event": "datasets_table_ready"})
            except Exception as exc:
                logger.warning({"event": "datasets_table_exists", "detail": truncate_error(exc, 100)})

    async def _ensure_chat_tables(self, db: Database) -> None:
        """Create sessions and messages tables in MySQL if they don't exist.

        Schema migrations should be managed via Alembic:
            alembic upgrade head
        """
        sessions_ddl = (
            "CREATE TABLE IF NOT EXISTS sessions ("
            "  id VARCHAR(64) PRIMARY KEY,"
            "  title VARCHAR(255) NOT NULL DEFAULT '新对话',"
            "  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,"
            "  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"
            ")"
        )
        messages_ddl = (
            "CREATE TABLE IF NOT EXISTS messages ("
            "  id INT AUTO_INCREMENT PRIMARY KEY,"
            "  session_id VARCHAR(64) NOT NULL,"
            "  role VARCHAR(16) NOT NULL,"
            "  content TEXT,"
            "  sql_text TEXT,"
            "  chart_type VARCHAR(32),"
            "  echarts_option JSON,"
            "  insight TEXT,"
            "  `columns` JSON,"
            "  rows_data JSON,"
            "  evidence JSON,"
            "  elapsed_ms FLOAT DEFAULT 0,"
            "  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,"
            "  INDEX idx_messages_session (session_id)"
            ")"
        )
        try:
            await db.execute(sessions_ddl)
            await db.execute(messages_ddl)
            logger.info({"event": "chat_tables_ready"})
        except Exception as exc:
            logger.warning({"event": "chat_tables_exists", "detail": truncate_error(exc, 100)})

        # Create mysql_connections table
        connections_ddl = (
            "CREATE TABLE IF NOT EXISTS mysql_connections ("
            "  id VARCHAR(36) PRIMARY KEY,"
            "  user_id VARCHAR(36) NOT NULL,"
            "  display_name VARCHAR(128),"
            "  host VARCHAR(255) NOT NULL,"
            "  port INT DEFAULT 3306,"
            "  `database` VARCHAR(128) NOT NULL,"
            "  username VARCHAR(128) NOT NULL,"
            "  encrypted_password VARCHAR(512) NOT NULL,"
            "  status VARCHAR(32) DEFAULT 'active',"
            "  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,"
            "  INDEX idx_conn_user (user_id)"
            ")"
        )
        try:
            await db.execute(connections_ddl)
        except Exception as exc:
            logger.warning({"event": "mysql_connections_table", "error": truncate_error(exc)})

        logger.info(
            {"event": "schema_migration_hint", "message": "For schema changes, use: alembic upgrade head"}
        )

    async def _load_datasets_from_mysql(self, db: Database, duckdb_engine: DuckDBEngine) -> None:
        """Load dataset metadata from MySQL into the registry."""
        import json as _json

        try:
            rows = await db.execute(
                "SELECT id, name, source_type, status, table_name, session_id, user_id, "
                "row_count, column_count, columns_meta, profile_meta "
                "FROM datasets WHERE status = 'ready'"
            )
        except Exception as exc:
            logger.warning({"event": "load_datasets_query_failed", "error": truncate_error(exc)})
            rows = []

        existing_tables = set(await asyncio.to_thread(duckdb_engine.tables))
        loaded = 0

        for row in rows:
            table_name = row["table_name"]
            # Skip if table no longer exists in DuckDB
            if table_name not in existing_tables:
                continue

            columns_meta = row.get("columns_meta")
            if isinstance(columns_meta, str):
                try:
                    columns_meta = _json.loads(columns_meta)
                except Exception as exc:
                    logger.warning({"event": "parse_columns_meta_failed", "table": table_name, "error": truncate_error(exc)})
                    columns_meta = []

            self.registry.register(
                table_name=table_name,
                display_name=row["name"],
                source_type=row["source_type"],
                session_id=row.get("session_id"),
                user_id=row.get("user_id"),
                columns_meta=columns_meta or [],
            )
            loaded += 1

        logger.info({"event": "datasets_loaded_from_mysql", "count": loaded})


async def ensure_bootstrap() -> None:
    """Ensure bootstrap has run. Safe to call multiple times."""
    await bootstrap.run()


# Module-level singleton
bootstrap = Bootstrap()
