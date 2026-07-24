"""DatasetManager — import Excel/CSV into DuckDB.

Handles the lifecycle of user-uploaded datasets:
- Excel (.xlsx/.xls) → pandas DataFrame → DuckDB table
- CSV → DuckDB read_csv (direct, no pandas)
- Delete dataset (DROP TABLE)
- List datasets

Usage:
    from app.services.dataset_manager import DatasetManager

    manager = DatasetManager(duckdb_engine, mysql_db)
    dataset = await manager.import_file("sales.xlsx", session_id="ses_abc")
    datasets = await manager.list_datasets("ses_abc")
    await manager.delete_dataset(dataset.id)
"""

import csv
import json
import logging
import os
import uuid
from dataclasses import dataclass, field
from typing import Optional

from app.tools.column_cleaner import clean_column_names, generate_table_name

logger = logging.getLogger("t2s_analysis")

# Limits
MAX_ROWS = 100_000
MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10MB

# Supported formats
_EXCEL_EXTENSIONS = {".xlsx", ".xls"}
_CSV_EXTENSIONS = {".csv"}


@dataclass
class DatasetInfo:
    """Metadata for an imported dataset."""
    id: str
    name: str
    source_type: str          # "excel" | "csv"
    status: str               # "uploading" | "ready" | "deleted"
    table_name: str           # DuckDB table name
    session_id: str
    row_count: int
    column_count: int
    columns_meta: list[dict]  # [{"name": "col1", "original_name": "原始名", "type": "VARCHAR"}, ...]
    original_file: str
    file_size_bytes: int
    sheet_name: Optional[str] = None
    profile_meta: Optional[dict] = None


class DatasetManager:
    """Import and manage user-updated datasets in DuckDB."""

    def __init__(
        self,
        duckdb_engine: object,
        mysql_db: object = None,
        registry: object = None,
        profiler: object = None,
    ) -> None:
        self._engine = duckdb_engine
        self._db = mysql_db
        self._registry = registry
        self._profiler = profiler

    async def import_file(
        self,
        file_path: str,
        session_id: str,
        display_name: Optional[str] = None,
    ) -> list[DatasetInfo]:
        """Import a file into DuckDB. Auto-detects format.

        Lifecycle: uploading → profile → ready → persist to MySQL.
        Returns a list of DatasetInfo (one per sheet for Excel, one for CSV).
        """
        ext = os.path.splitext(file_path)[1].lower()
        original_name = display_name or os.path.basename(file_path)
        file_size = os.path.getsize(file_path)

        if file_size > MAX_FILE_SIZE_BYTES:
            raise ValueError(f"File too large: {file_size} bytes (max {MAX_FILE_SIZE_BYTES})")

        if ext in _EXCEL_EXTENSIONS:
            datasets = await self._import_excel(file_path, original_name, session_id, file_size)
        elif ext in _CSV_EXTENSIONS:
            datasets = [await self._import_csv(file_path, original_name, session_id, file_size)]
        else:
            raise ValueError(f"Unsupported file format: {ext}")

        # Post-import: generate profile, persist to MySQL, register
        for ds in datasets:
            ds.status = "uploading"
            ds.profile_meta = self._generate_profile(ds.table_name)
            ds.status = "ready"

            await self._persist_to_mysql(ds)

            if self._registry:
                self._registry.register(
                    table_name=ds.table_name,
                    display_name=ds.name,
                    source_type=ds.source_type,
                    session_id=ds.session_id,
                    columns_meta=ds.columns_meta,
                )

        return datasets

    async def _import_excel(
        self,
        file_path: str,
        original_name: str,
        session_id: str,
        file_size: int,
    ) -> list[DatasetInfo]:
        """Import Excel file (all sheets) into DuckDB."""
        import pandas as pd

        # Read all sheets
        xls = pd.ExcelFile(file_path)
        datasets = []

        for sheet_name in xls.sheet_names:
            # Auto-detect header row: skip empty/title rows at the top
            df_raw = pd.read_excel(xls, sheet_name=sheet_name, header=None, nrows=10)
            header_row = 0

            for i in range(min(10, len(df_raw))):
                row = df_raw.iloc[i]
                non_null = [v for v in row if pd.notna(v)]

                if len(non_null) < 2:
                    continue  # Too few values, skip

                # Count string values (headers are mostly text)
                str_count = sum(1 for v in non_null if isinstance(v, str))

                # If most non-null values are strings, this is the header row
                if str_count >= max(2, len(non_null) * 0.4):
                    header_row = i
                    break

            df = pd.read_excel(xls, sheet_name=sheet_name, header=header_row)

            # Drop fully empty rows and reset index
            df = df.dropna(how="all").reset_index(drop=True)

            # Drop rows that look like sub-headers (all string values matching column names)
            if len(df) > 0:
                first_row = df.iloc[0]
                if all(isinstance(v, str) for v in first_row.dropna()):
                    # Check if this row looks like a repeated header
                    overlap = sum(1 for v in first_row.dropna() if v in str(list(df.columns)))
                    if overlap >= len(df.columns) * 0.3:
                        df = df.iloc[1:].reset_index(drop=True)

            # Auto-convert numeric columns (pandas may read them as object due to header issues)
            for col in df.columns:
                if df[col].dtype == object:
                    # Try to convert to numeric
                    numeric = pd.to_numeric(df[col], errors="coerce")
                    # If most values converted successfully, use numeric version
                    if numeric.notna().sum() >= len(df) * 0.5:
                        df[col] = numeric

            if len(df) > MAX_ROWS:
                df = df.head(MAX_ROWS)
                logger.warning({
                    "event": "dataset_truncated",
                    "sheet": sheet_name,
                    "max_rows": MAX_ROWS,
                })

            if df.empty:
                logger.warning({"event": "empty_sheet", "sheet": sheet_name})
                continue

            # Clean column names
            original_columns = list(df.columns)
            cleaned_columns = clean_column_names(original_columns)
            df.columns = cleaned_columns

            # Generate table name
            table_name = generate_table_name(original_name, sheet_name)
            dataset_id = str(uuid.uuid4())

            # Import into DuckDB — register DataFrame first
            self._engine.execute(f'DROP TABLE IF EXISTS "{table_name}"')
            self._engine.conn.register("_tmp_df", df)
            self._engine.execute(
                f'CREATE TABLE "{table_name}" AS SELECT * FROM _tmp_df'
            )
            self._engine.conn.unregister("_tmp_df")

            # Build column metadata
            columns_meta = []
            for i, (cleaned, original) in enumerate(zip(cleaned_columns, original_columns)):
                col_type = str(df[cleaned].dtype)
                # Map pandas dtype to SQL type
                sql_type = self._pandas_to_sql_type(col_type)
                columns_meta.append({
                    "name": cleaned,
                    "original_name": str(original),
                    "type": sql_type,
                })

            dataset = DatasetInfo(
                id=dataset_id,
                name=f"{original_name} ({sheet_name})" if len(xls.sheet_names) > 1 else original_name,
                source_type="excel",
                status="uploading",
                table_name=table_name,
                session_id=session_id,
                row_count=len(df),
                column_count=len(cleaned_columns),
                columns_meta=columns_meta,
                original_file=original_name,
                file_size_bytes=file_size,
                sheet_name=sheet_name,
            )
            datasets.append(dataset)

            logger.info({
                "event": "dataset_imported",
                "table": table_name,
                "rows": len(df),
                "columns": len(cleaned_columns),
                "source": "excel",
            })

        xls.close()
        return datasets

    async def _import_csv(
        self,
        file_path: str,
        original_name: str,
        session_id: str,
        file_size: int,
    ) -> DatasetInfo:
        """Import CSV file into DuckDB (direct read, no pandas)."""
        # Generate table name
        table_name = generate_table_name(original_name)
        dataset_id = str(uuid.uuid4())

        # Import directly with DuckDB
        self._engine.execute(f'DROP TABLE IF EXISTS "{table_name}"')
        self._engine.execute(
            f"CREATE TABLE \"{table_name}\" AS SELECT * FROM read_csv('{file_path}', header=true, auto_detect=true)"
        )

        # Get column info from DuckDB
        desc = self._engine.execute(f'DESCRIBE "{table_name}"').fetchall()
        columns_meta = []
        for row in desc:
            col_name = row[0]
            col_type = row[1]
            columns_meta.append({
                "name": col_name,
                "original_name": col_name,
                "type": col_type,
            })

        # Get row count
        count_result = self._engine.execute(f'SELECT COUNT(*) FROM "{table_name}"').fetchone()
        row_count = count_result[0] if count_result else 0

        # Truncate if needed (CSV can be large)
        if row_count > MAX_ROWS:
            self._engine.execute(
                f'CREATE OR REPLACE TABLE "{table_name}" AS '
                f'SELECT * FROM "{table_name}" LIMIT {MAX_ROWS}'
            )
            row_count = MAX_ROWS
            logger.warning({"event": "dataset_truncated", "table": table_name, "max_rows": MAX_ROWS})

        dataset = DatasetInfo(
            id=dataset_id,
            name=original_name,
            source_type="csv",
            status="uploading",
            table_name=table_name,
            session_id=session_id,
            row_count=row_count,
            column_count=len(columns_meta),
            columns_meta=columns_meta,
            original_file=original_name,
            file_size_bytes=file_size,
        )

        logger.info({
            "event": "dataset_imported",
            "table": table_name,
            "rows": row_count,
            "columns": len(columns_meta),
            "source": "csv",
        })

        return dataset

    async def delete_dataset(self, table_name: str) -> None:
        """Delete a dataset: DROP TABLE + unregister + mark deleted in MySQL."""
        self._engine.execute(f'DROP TABLE IF EXISTS "{table_name}"')

        if self._registry:
            self._registry.unregister(table_name)

        await self._update_status_mysql(table_name, "deleted")
        logger.info({"event": "dataset_deleted", "table": table_name})

    async def archive_dataset(self, table_name: str) -> None:
        """Archive a dataset: hide from catalog but keep DuckDB table."""
        if self._registry:
            self._registry.unregister(table_name)

        await self._update_status_mysql(table_name, "archived")
        logger.info({"event": "dataset_archived", "table": table_name})

    def list_tables(self) -> list[str]:
        """List all tables in DuckDB."""
        return self._engine.tables()

    # ── MySQL persistence ─────────────────────────────────

    async def _persist_to_mysql(self, ds: "DatasetInfo") -> None:
        """Persist dataset metadata to MySQL datasets table."""
        if self._db is None:
            return
        try:
            await self._db.execute(
                "INSERT INTO datasets "
                "(id, name, source_type, status, table_name, session_id, "
                "row_count, column_count, columns_meta, profile_meta, original_file, file_size_bytes) "
                "VALUES (:id, :name, :source_type, :status, :table_name, :session_id, "
                ":row_count, :column_count, :columns_meta, :profile_meta, :original_file, :file_size_bytes)",
                {
                    "id": ds.id,
                    "name": ds.name,
                    "source_type": ds.source_type,
                    "status": ds.status,
                    "table_name": ds.table_name,
                    "session_id": ds.session_id,
                    "row_count": ds.row_count,
                    "column_count": ds.column_count,
                    "columns_meta": json.dumps(ds.columns_meta, ensure_ascii=False),
                    "profile_meta": json.dumps(ds.profile_meta, ensure_ascii=False) if ds.profile_meta else None,
                    "original_file": ds.original_file,
                    "file_size_bytes": ds.file_size_bytes,
                },
            )
            logger.info({"event": "dataset_persisted", "table": ds.table_name})
        except Exception as exc:
            logger.error({"event": "dataset_persist_failed", "table": ds.table_name, "error": str(exc)})

    async def _update_status_mysql(self, table_name: str, status: str) -> None:
        """Update dataset status in MySQL."""
        if self._db is None:
            return
        try:
            await self._db.execute(
                "UPDATE datasets SET status = :status WHERE table_name = :table",
                {"status": status, "table": table_name},
            )
        except Exception as exc:
            logger.error({"event": "dataset_status_update_failed", "table": table_name, "error": str(exc)})

    def _generate_profile(self, table_name: str) -> Optional[dict]:
        """Generate data profile for a table."""
        if self._profiler is None:
            return None
        try:
            return self._profiler.profile(table_name)
        except Exception as exc:
            logger.warning({"event": "profile_generation_failed", "table": table_name, "error": str(exc)})
            return None

    @staticmethod
    def _pandas_to_sql_type(pd_type: str) -> str:
        """Map pandas dtype string to SQL type name."""
        pd_type = pd_type.lower()
        if "int" in pd_type:
            return "BIGINT"
        if "float" in pd_type or "double" in pd_type:
            return "DOUBLE"
        if "datetime" in pd_type or "timestamp" in pd_type:
            return "TIMESTAMP"
        if "date" in pd_type:
            return "DATE"
        if "bool" in pd_type:
            return "BOOLEAN"
        return "VARCHAR"
