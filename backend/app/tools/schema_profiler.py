"""SchemaProfiler — generate data profiles for DuckDB tables.

Generates column-level and table-level statistics including:
- Data type and semantic type (dimension/measure/time/identifier/text)
- NULL ratio, unique count
- Min/max values, top 5 most frequent values
- Date range for time columns

Usage:
    from app.tools.schema_profiler import SchemaProfiler

    profiler = SchemaProfiler(duckdb_engine)
    profile = profiler.profile("orders")
    # {"table": "orders", "row_count": 50, "columns": [...]}
"""

import logging
from typing import Optional

logger = logging.getLogger("t2s_analysis")

# Semantic type constants
DIMENSION = "dimension"
MEASURE = "measure"
TIME = "time"
IDENTIFIER = "identifier"
TEXT = "text"

# Numeric SQL types
_NUMERIC_TYPES = {
    "TINYINT", "SMALLINT", "INTEGER", "BIGINT", "HUGEINT",
    "FLOAT", "DOUBLE", "REAL", "DECIMAL", "NUMERIC",
}

# Time SQL types
_TIME_TYPES = {"DATE", "TIMESTAMP", "TIMESTAMP WITH TIME ZONE", "TIMESTAMPTZ", "TIME"}

# Patterns that suggest identifier columns
_IDENTIFIER_PATTERNS = {"_id", "id_", "code", "no", "number", "key", "uuid", "guid"}


class SchemaProfiler:
    """Generate data profiles for DuckDB tables."""

    def __init__(self, duckdb_engine: object) -> None:
        self._engine = duckdb_engine

    def profile(self, table_name: str) -> dict:
        """Generate a full profile for a DuckDB table.

        Returns:
            {
                "table": "orders",
                "row_count": 50,
                "column_count": 7,
                "columns": [
                    {
                        "name": "customer_id",
                        "type": "VARCHAR",
                        "semantic_type": "identifier",
                        "null_ratio": 0.0,
                        "unique_count": 15,
                        "min": None,
                        "max": None,
                        "top_values": ["C001", "C002", "C003"]
                    },
                    ...
                ]
            }
        """
        # 1. Get column schema
        desc = self._engine.execute(f'DESCRIBE "{table_name}"').fetchall()
        # desc: [(col_name, col_type, null, key, default, extra), ...]

        # 2. Get row count
        count_result = self._engine.execute(f'SELECT COUNT(*) FROM "{table_name}"').fetchone()
        row_count = count_result[0] if count_result else 0

        # 3. Profile each column
        columns = []
        for col_info in desc:
            col_name = col_info[0]
            col_type = col_info[1].upper() if col_info[1] else "VARCHAR"
            col_profile = self._profile_column(table_name, col_name, col_type, row_count)
            columns.append(col_profile)

        return {
            "table": table_name,
            "row_count": row_count,
            "column_count": len(columns),
            "columns": columns,
        }

    def _profile_column(
        self, table: str, col_name: str, col_type: str, row_count: int
    ) -> dict:
        """Profile a single column."""
        # Escape column name for SQL
        safe_col = f'"{col_name}"'
        safe_table = f'"{table}"'

        # NULL ratio
        null_count = 0
        if row_count > 0:
            result = self._engine.execute(
                f"SELECT COUNT(*) FROM {safe_table} WHERE {safe_col} IS NULL"
            ).fetchone()
            null_count = result[0] if result else 0
        null_ratio = round(null_count / row_count, 4) if row_count > 0 else 0.0

        # Unique count
        result = self._engine.execute(
            f"SELECT COUNT(DISTINCT {safe_col}) FROM {safe_table}"
        ).fetchone()
        unique_count = result[0] if result else 0

        # Determine base type for further analysis
        base_type = self._normalize_type(col_type)

        # Min/max for numeric and time columns
        min_val, max_val = None, None
        if base_type in ("numeric", "time"):
            try:
                result = self._engine.execute(
                    f"SELECT MIN({safe_col}), MAX({safe_col}) FROM {safe_table}"
                ).fetchone()
                if result:
                    min_val = str(result[0]) if result[0] is not None else None
                    max_val = str(result[1]) if result[1] is not None else None
            except Exception:
                pass

        # Top values (for low-cardinality columns)
        top_values = []
        if unique_count <= 50 and row_count > 0:
            try:
                result = self._engine.execute(
                    f"SELECT {safe_col}, COUNT(*) as cnt FROM {safe_table} "
                    f"WHERE {safe_col} IS NOT NULL "
                    f"GROUP BY {safe_col} ORDER BY cnt DESC LIMIT 5"
                ).fetchall()
                top_values = [str(r[0]) for r in result]
            except Exception:
                pass

        # Semantic type
        semantic_type = self._infer_semantic_type(
            col_name, col_type, base_type, unique_count, row_count
        )

        return {
            "name": col_name,
            "type": col_type,
            "semantic_type": semantic_type,
            "null_ratio": null_ratio,
            "unique_count": unique_count,
            "min": min_val,
            "max": max_val,
            "top_values": top_values,
        }

    def _infer_semantic_type(
        self,
        col_name: str,
        col_type: str,
        base_type: str,
        unique_count: int,
        row_count: int,
    ) -> str:
        """Infer the semantic type of a column.

        Priority:
        1. ID patterns in column name → identifier
        2. Time types → time
        3. Numeric + low cardinality (< 20 unique or < 5% unique ratio) → dimension
        4. Numeric + high cardinality → measure
        5. Text + low cardinality → dimension
        6. Text + high cardinality → text
        """
        name_lower = col_name.lower()

        # 1. Identifier patterns
        for pattern in _IDENTIFIER_PATTERNS:
            if pattern in name_lower:
                return IDENTIFIER

        # 2. Time types
        if base_type == "time":
            return TIME

        # 3-4. Numeric columns
        if base_type == "numeric":
            unique_ratio = unique_count / row_count if row_count > 0 else 1.0
            if unique_count <= 20 or unique_ratio < 0.05:
                return DIMENSION
            return MEASURE

        # 5-6. Text columns
        if base_type == "text":
            unique_ratio = unique_count / row_count if row_count > 0 else 1.0
            if unique_count <= 50 or unique_ratio < 0.1:
                return DIMENSION
            return TEXT

        return TEXT

    @staticmethod
    def _normalize_type(col_type: str) -> str:
        """Normalize SQL type to a base category: numeric, time, text."""
        col_type = col_type.upper()
        # Strip parameters: VARCHAR(255) → VARCHAR
        base = col_type.split("(")[0].strip()

        if base in _NUMERIC_TYPES:
            return "numeric"
        if base in _TIME_TYPES:
            return "time"
        return "text"
