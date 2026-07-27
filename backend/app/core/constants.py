"""Shared constants."""

# Numeric SQL types used by chart detection and schema profiler.
NUMERIC_SQL_TYPES: frozenset[str] = frozenset({
    # Uppercase full names (used by schema_profiler for DESCRIBE output)
    "TINYINT", "SMALLINT", "INTEGER", "BIGINT", "FLOAT", "DOUBLE",
    "DECIMAL", "NUMERIC", "REAL",
    # Lowercase short names (used by chart detection)
    "int", "integer", "bigint", "float", "double", "decimal", "numeric", "real",
    "tinyint", "smallint",
})
