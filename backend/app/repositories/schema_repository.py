"""Repository for reading MySQL schema metadata from information_schema."""

from typing import Optional

from app.core.database import Database


class SchemaRepository:
    """Read-only repository for database schema metadata."""

    def __init__(self, db: Optional[Database] = None) -> None:
        """Allow injection for testing; default to the global instance."""
        from app.core.database import db as _db

        self._db = db or _db

    async def get_tables(self) -> list[dict]:
        """Return all user tables with table_name and table_comment."""
        sql = (
            "SELECT TABLE_NAME AS table_name, TABLE_COMMENT AS table_comment "
            "FROM information_schema.tables "
            "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_TYPE = 'BASE TABLE' "
            "ORDER BY TABLE_NAME"
        )
        return await self._db.execute(sql)

    async def get_columns(self, table: str) -> list[dict]:
        """Return columns for a table with name, type, nullable, default, comment."""
        sql = (
            "SELECT COLUMN_NAME AS column_name, "
            "       DATA_TYPE AS data_type, "
            "       IS_NULLABLE AS is_nullable, "
            "       COLUMN_DEFAULT AS column_default, "
            "       COLUMN_COMMENT AS column_comment "
            "FROM information_schema.columns "
            "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = :table_name "
            "ORDER BY ORDINAL_POSITION"
        )
        return await self._db.execute(sql, {"table_name": table})

    async def get_foreign_keys(self) -> list[dict]:
        """Return all foreign key relationships in the database."""
        sql = (
            "SELECT "
            "  kcu.TABLE_NAME AS table_name, "
            "  kcu.COLUMN_NAME AS column_name, "
            "  kcu.REFERENCED_TABLE_NAME AS ref_table_name, "
            "  kcu.REFERENCED_COLUMN_NAME AS ref_column_name "
            "FROM information_schema.key_column_usage kcu "
            "WHERE kcu.TABLE_SCHEMA = DATABASE() "
            "  AND kcu.REFERENCED_TABLE_NAME IS NOT NULL "
            "ORDER BY kcu.TABLE_NAME, kcu.ORDINAL_POSITION"
        )
        return await self._db.execute(sql)

    async def get_sample_rows(
        self, table: str, limit: int = 3
    ) -> list[dict]:
        """Return sample rows from a table. Table name is validated against
        existing tables to prevent SQL identifier injection."""
        allowed = {t["table_name"] for t in await self.get_tables()}
        if table not in allowed:
            raise ValueError(
                f"Unknown table '{table}'. "
                f"Allowed tables: {', '.join(sorted(allowed))}"
            )
        sql = f"SELECT * FROM `{table}` LIMIT :limit"
        return await self._db.execute(sql, {"limit": limit})
