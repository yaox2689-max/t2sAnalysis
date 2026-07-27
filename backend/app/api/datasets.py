"""Dataset API — file upload, listing, deletion.

Endpoints:
    POST /api/datasets/upload   — Upload Excel/CSV, import into DuckDB
    GET  /api/datasets          — List session's datasets
    DELETE /api/datasets/{id}   — Delete a dataset
"""

import logging
import os
import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from app.core.auth import get_current_user
from app.services.auth_service import UserOut

logger = logging.getLogger("t2s_analysis")

router = APIRouter(prefix="/api/datasets", tags=["datasets"])

# Upload directory
_UPLOAD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "uploads")

# Allowed extensions
_ALLOWED_EXTENSIONS = {".xlsx", ".xls", ".csv"}


async def _ensure_bootstrap():
    """Ensure bootstrap is initialized and return it."""
    from app.bootstrap import bootstrap
    if not bootstrap._initialized:
        await bootstrap.run()
    return bootstrap


def _ensure_upload_dir():
    os.makedirs(_UPLOAD_DIR, exist_ok=True)


@router.post("/upload")
async def upload_dataset(
    file: UploadFile = File(...),
    session_id: str = Form(...),
    user: UserOut = Depends(get_current_user),
):
    """Upload an Excel/CSV file and import into DuckDB.

    Returns dataset metadata including preview data.
    """
    bootstrap = await _ensure_bootstrap()

    # Verify session belongs to user
    from app.core.database import db as _db
    sess = await _db.execute(
        "SELECT id FROM sessions WHERE id = :sid AND user_id = :uid",
        {"sid": session_id, "uid": user.id},
    )
    if not sess:
        raise HTTPException(status_code=404, detail="Session not found")

    # Validate extension
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in _ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Unsupported format: {ext}")

    # Save to temp file
    _ensure_upload_dir()
    file_id = uuid.uuid4().hex[:12]
    safe_name = f"{file_id}{ext}"
    temp_path = os.path.join(_UPLOAD_DIR, safe_name)

    try:
        # Save uploaded file
        with open(temp_path, "wb") as f:
            content = await file.read()
            f.write(content)

        # Import into DuckDB (handles profiling, MySQL persist, registry)
        datasets = await bootstrap.dataset_manager.import_file(
            temp_path,
            session_id=session_id,
            display_name=file.filename,
            user_id=user.id,
        )

        # Get preview (first 5 rows) with profile
        previews = []
        for ds in datasets:
            try:
                result = bootstrap.executor._engine.execute(
                    f'SELECT * FROM "{ds.table_name}" LIMIT 5'
                ).fetchdf()
                preview_rows = result.to_dict("records")

                # Build enriched columns with profile info
                enriched_columns = ds.columns_meta.copy()
                if ds.profile_meta and "columns" in ds.profile_meta:
                    for col_info in ds.profile_meta["columns"]:
                        # Match by column name
                        for ec in enriched_columns:
                            if ec.get("name") == col_info.get("name"):
                                ec["semantic_type"] = col_info.get("semantic_type", "text")
                                ec["null_ratio"] = col_info.get("null_ratio", 0)
                                ec["unique_count"] = col_info.get("unique_count", 0)
                                ec["top_values"] = col_info.get("top_values", [])
                                if col_info.get("min"):
                                    ec["min"] = col_info["min"]
                                    ec["max"] = col_info["max"]
                                break

                previews.append({
                    "dataset_id": ds.id,
                    "table_name": ds.table_name,
                    "name": ds.name,
                    "source_type": ds.source_type,
                    "sheet_name": ds.sheet_name,
                    "row_count": ds.row_count,
                    "column_count": ds.column_count,
                    "columns": enriched_columns,
                    "preview_rows": preview_rows,
                    "profile": ds.profile_meta,
                })
            except Exception as exc:
                logger.warning({"event": "preview_build_failed", "table": ds.table_name, "error": str(exc)[:200]})
                previews.append({
                    "dataset_id": ds.id,
                    "table_name": ds.table_name,
                    "name": ds.name,
                    "row_count": ds.row_count,
                    "column_count": ds.column_count,
                    "columns": ds.columns_meta,
                    "preview_rows": [],
                })

        return {"datasets": previews, "count": len(previews)}

    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Import failed: {str(exc)[:200]}")


@router.get("")
async def list_datasets(session_id: str, user: UserOut = Depends(get_current_user)):
    """List all datasets for a session (owned by current user)."""
    bootstrap = await _ensure_bootstrap()

    catalog = bootstrap.registry.get_catalog(session_id=session_id, user_id=user.id, top_k=100)
    datasets = []
    for table in catalog.tables:
        datasets.append({
            "table_name": table.table_name,
            "name": table.display_name,
            "source_type": table.source_type,
            "row_count": table.row_count,
            "column_count": len(table.columns),
            "columns": [
                {"name": c.name, "type": c.data_type, "semantic_type": c.semantic_type}
                for c in table.columns
            ],
        })

    return {"datasets": datasets, "count": len(datasets)}


@router.delete("/{table_name}")
async def delete_dataset(table_name: str, user: UserOut = Depends(get_current_user)):
    """Delete a dataset (owned by current user)."""
    bootstrap = await _ensure_bootstrap()

    # Check if table exists and belongs to user
    meta = bootstrap.registry._index.get(table_name)
    if not meta:
        raise HTTPException(status_code=404, detail="Dataset not found")
    if meta.get("user_id") and meta["user_id"] != user.id:
        raise HTTPException(status_code=403, detail="Not your dataset")

    # Drop from DuckDB
    await bootstrap.dataset_manager.delete_dataset(table_name)

    # Unregister from catalog
    bootstrap.registry.unregister(table_name)

    return {"ok": True, "deleted": table_name}
