"""Bootstrap — system startup initialization.

Run once on application start:
1. Open DuckDB connection
2. Import demo seed data (if not already present)
3. Initialize DatasetRegistry
4. Initialize PromptBuilder

Usage:
    from app.bootstrap import bootstrap

    await bootstrap.run()
"""

import csv
import logging
import os
import uuid
from pathlib import Path

logger = logging.getLogger("t2s_analysis")

# Seed CSV directory
_SEED_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts", "seed")

# Demo datasets: CSV filename → human-readable name
_DEMO_DATASETS = {
    "orders": "Olist Orders",
    "customers": "Olist Customers",
    "products": "Olist Products",
    "payments": "Olist Payments",
    "order_items": "Olist Order Items",
    "sellers": "Olist Sellers",
    "product_category": "Olist Product Categories",
    "reviews": "Olist Reviews",
}


class Bootstrap:
    """System startup orchestrator."""

    def __init__(self) -> None:
        self._initialized = False
        self.profiler = None
        self.registry = None
        self.prompt_builder = None
        self.executor = None
        self.dataset_manager = None

    async def run(self) -> None:
        """Full startup sequence."""
        if self._initialized:
            return

        logger.info({"event": "bootstrap_start"})

        # 1. Init DuckDB
        from app.core.duckdb import duckdb_engine
        duckdb_engine.init()
        logger.info({"event": "bootstrap_duckdb_ready"})

        # 2. Init MySQL (business metadata)
        from app.core.database import db
        db.init()
        await self._ensure_datasets_table(db)
        await self._ensure_chat_tables(db)

        # 3. Demo data disabled — user only wants to analyze uploaded files
        # self._init_demo_data(duckdb_engine)

        # 4. Init SchemaProfiler
        from app.tools.schema_profiler import SchemaProfiler
        self.profiler = SchemaProfiler(duckdb_engine)

        # 5. Init DatasetRegistry + load from MySQL
        from app.services.dataset_registry import DatasetRegistry
        self.registry = DatasetRegistry(duckdb_engine, self.profiler)
        await self._load_datasets_from_mysql(db, duckdb_engine)

        # 6. Init PromptBuilder (with DuckDB engine for sample rows)
        from app.services.prompt_builder import PromptBuilder
        self.prompt_builder = PromptBuilder(duckdb_engine=duckdb_engine)

        # 7. Init DuckDBExecutor
        from app.tools.duckdb_executor import DuckDBExecutor
        from app.core.config import settings as _settings
        self.executor = DuckDBExecutor(duckdb_engine, timeout=_settings.SQL_TIMEOUT)

        # 8. Init DatasetManager
        from app.services.dataset_manager import DatasetManager
        self.dataset_manager = DatasetManager(duckdb_engine, db, self.registry, self.profiler)

        # 9. Log final state
        tables = duckdb_engine.tables()
        logger.info({"event": "bootstrap_complete", "tables": tables})

        self._initialized = True

    async def _ensure_datasets_table(self, db: object) -> None:
        """Create datasets table in MySQL if it doesn't exist."""
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
                logger.warning({"event": "datasets_table_exists", "detail": str(exc)[:100]})

    async def _ensure_chat_tables(self, db: object) -> None:
        """Create sessions and messages tables in MySQL if they don't exist."""
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
            logger.warning({"event": "chat_tables_exists", "detail": str(exc)[:100]})

    async def _load_datasets_from_mysql(self, db: object, duckdb_engine: object) -> None:
        """Load dataset metadata from MySQL into the registry."""
        import json as _json

        try:
            rows = await db.execute(
                "SELECT id, name, source_type, status, table_name, session_id, "
                "row_count, column_count, columns_meta, profile_meta "
                "FROM datasets WHERE status = 'ready'"
            )
        except Exception:
            rows = []

        existing_tables = set(duckdb_engine.tables())
        loaded = 0

        for row in rows:
            table_name = row["table_name"]
            # Skip if table no longer exists in DuckDB
            if table_name not in existing_tables:
                continue

            # Skip demo data — only load user-uploaded datasets
            if row["source_type"] == "demo":
                continue

            columns_meta = row.get("columns_meta")
            if isinstance(columns_meta, str):
                try:
                    columns_meta = _json.loads(columns_meta)
                except Exception:
                    columns_meta = []

            self.registry.register(
                table_name=table_name,
                display_name=row["name"],
                source_type=row["source_type"],
                session_id=row.get("session_id"),
                columns_meta=columns_meta or [],
            )
            loaded += 1

        # Demo auto-registration disabled — only user-uploaded data is visible
        # for table_name in duckdb_engine.tables():
        #     if table_name not in self.registry.list_tables():
        #         ...

        logger.info({"event": "datasets_loaded_from_mysql", "count": loaded})

    def _init_demo_data(self, engine: object) -> None:
        """Import seed CSVs into DuckDB if demo tables don't exist."""
        from app.core.duckdb import DuckDBEngine
        engine: DuckDBEngine

        existing = set(engine.tables())

        # Check if any demo data already exists
        if any(name in existing for name in _DEMO_DATASETS):
            logger.info({"event": "demo_data_exists", "tables": list(existing)})
            return

        if not os.path.isdir(_SEED_DIR):
            logger.warning({"event": "seed_dir_missing", "path": _SEED_DIR})
            return

        imported = []
        for csv_name, display_name in _DEMO_DATASETS.items():
            csv_path = os.path.join(_SEED_DIR, f"{csv_name}.csv")
            if not os.path.exists(csv_path):
                logger.warning({"event": "seed_csv_missing", "file": csv_name})
                continue

            # Use the CSV name directly as table name (readable in SHOW TABLES)
            table_name = csv_name
            engine.execute(
                f"CREATE TABLE \"{table_name}\" AS SELECT * FROM read_csv('{csv_path}', header=true, auto_detect=true)"
            )
            imported.append(table_name)
            logger.info({"event": "demo_table_imported", "table": table_name, "source": csv_name})

        if imported:
            logger.info({"event": "demo_data_imported", "count": len(imported), "tables": imported})
        else:
            logger.warning({"event": "demo_data_none_imported"})


# Module-level singleton
bootstrap = Bootstrap()
