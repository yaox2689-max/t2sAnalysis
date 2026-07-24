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

    async def run(self) -> None:
        """Full startup sequence."""
        if self._initialized:
            return

        logger.info({"event": "bootstrap_start"})

        # 1. Init DuckDB
        from app.core.duckdb import duckdb_engine
        duckdb_engine.init()
        logger.info({"event": "bootstrap_duckdb_ready"})

        # 2. Import demo data if needed
        self._init_demo_data(duckdb_engine)

        # 3. Log final state
        tables = duckdb_engine.tables()
        logger.info({"event": "bootstrap_complete", "tables": tables})

        self._initialized = True

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
