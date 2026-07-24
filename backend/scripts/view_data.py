"""Quick viewer for DuckDB data.

Usage: Stop the backend first, then run:
    python scripts/view_data.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import duckdb

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "analysis.duckdb")

conn = duckdb.connect(DB_PATH, read_only=True)

# List all tables
tables = conn.execute("SHOW TABLES").fetchall()
print(f"\n{'='*60}")
print(f" DuckDB Tables: {len(tables)}")
print(f"{'='*60}")
for t in tables:
    name = t[0]
    count = conn.execute(f'SELECT COUNT(*) FROM "{name}"').fetchone()[0]
    print(f"  {name}: {count} rows")

# Show each table's data
for t in tables:
    name = t[0]
    print(f"\n{'='*60}")
    print(f" Table: {name}")
    print(f"{'='*60}")
    df = conn.execute(f'SELECT * FROM "{name}" LIMIT 50').fetchdf()
    print(df.to_string())
    print()

conn.close()
