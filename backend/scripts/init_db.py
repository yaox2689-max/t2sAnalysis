"""Olist dataset initialization script.

Usage:
    python init_db.py

Prerequisites:
    1. Download Olist dataset from Kaggle:
       https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce
    2. Extract CSV files to backend/scripts/olist_data/

This script is idempotent: running it multiple times produces the
same database state (DROP → CREATE → INSERT).
"""

import csv
import os
import sys

import pymysql

# ── Ensure app package is importable ──────────────────
# So that from app.core.config import settings works.
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(SCRIPT_DIR, ".."))

from app.core.config import settings  # noqa: E402

DATA_DIR = os.path.join(SCRIPT_DIR, "olist_data")
SCHEMA_PATH = os.path.join(SCRIPT_DIR, "schema.sql")

# ── CSV file → table mapping ───────────────────────────
CSV_TABLES = [
    # product_category must precede products (FK dependency)
    ("product_category_name_translation.csv",   "product_category"),
    ("olist_customers_dataset.csv",             "customers"),
    ("olist_sellers_dataset.csv",               "sellers"),
    ("olist_products_dataset.csv",              "products"),
    ("olist_orders_dataset.csv",                "orders"),
    ("olist_order_payments_dataset.csv",        "payments"),
    ("olist_order_items_dataset.csv",           "order_items"),
    ("olist_order_reviews_dataset.csv",         "reviews"),
]

BATCH_SIZE = 500


# ── Helpers ────────────────────────────────────────────

def get_db_config() -> dict:
    """Build pymysql connection params from project config.

    Connects without specifying a database so that ensure_database()
    can CREATE it first, then USE it.
    """
    return {
        "host": settings.DB_HOST,
        "port": settings.DB_PORT,
        "user": settings.DB_USER,
        "password": settings.DB_PASSWORD,
        "charset": "utf8mb4",
    }


def ensure_database(cursor):
    """Create database if it does not exist."""
    cursor.execute(
        f"CREATE DATABASE IF NOT EXISTS `{settings.DB_NAME}` "
        f"CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
    )


def run_schema(cursor):
    """Execute schema.sql to create all tables.

    Note: this uses a simple ";" split which works for plain DDL.
    It does NOT handle stored procedures, triggers, or semicolons
    inside string literals.
    """
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        sql = f.read()
    for statement in sql.split(";"):
        stmt = statement.strip()
        if stmt:
            cursor.execute(stmt + ";")
    print("  ✓ Schema created")


def insert_csv(cursor, csv_name: str, table: str):
    """Load a CSV file into the given table, streaming row by row."""
    path = os.path.join(DATA_DIR, csv_name)
    if not os.path.exists(path):
        print(f"  ⚠  File not found: {csv_name}, skipping")
        return

    with open(path, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        headers = next(reader)

        columns = ", ".join(f"`{h}`" for h in headers)
        placeholders = ", ".join(["%s"] * len(headers))
        sql = f"INSERT INTO `{table}` ({columns}) VALUES ({placeholders})"

        batch: list[list[str]] = []
        total = 0
        for row in reader:
            batch.append(row)
            total += 1
            if len(batch) >= BATCH_SIZE:
                cursor.executemany(sql, batch)
                batch.clear()
        if batch:
            cursor.executemany(sql, batch)

    print(f"  ✓ {table}: {total} rows")


def validate_tables(cursor):
    """Verify each table has data using accurate COUNT(*)."""
    print("\n  ── Validation ──────────────────────")
    for _, table_name in CSV_TABLES:
        cursor.execute(f"SELECT COUNT(*) FROM `{table_name}`")
        count = cursor.fetchone()[0]
        status = "✓" if count > 0 else "✗"
        print(f"  {status} {table_name}: {count} rows")
    print("  ────────────────────────────────────")


# ── Main ───────────────────────────────────────────────

def main():
    config = get_db_config()
    print(f"Connecting to {config['host']}:{config['port']} ...")

    conn = pymysql.connect(**config)
    cursor = conn.cursor()

    try:
        print("  ✓ Connected")

        # Step 1: ensure database exists
        ensure_database(cursor)
        cursor.execute(f"USE `{settings.DB_NAME}`")
        print(f"  ✓ Database `{settings.DB_NAME}` ready")

        # Step 2: run schema (DROP → CREATE)
        run_schema(cursor)

        # Step 3: import CSV data
        print("\n  ── Importing data ─────────────────")
        for csv_file, table in CSV_TABLES:
            insert_csv(cursor, csv_file, table)

        # Step 4: validate
        validate_tables(cursor)

        conn.commit()
        print("\n  ✓ Initialization complete")

    except Exception:
        conn.rollback()
        print("\n  ✗ Initialization failed, rolled back")
        raise
    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    main()
