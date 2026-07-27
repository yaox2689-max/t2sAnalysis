"""Connections API — manage MySQL direct-connection data sources.

Endpoints (all require auth):
    POST /api/connections/test  — Test a connection without saving
    POST /api/connections       — Save connection + register tables
    GET  /api/connections       — List user's connections
    DELETE /api/connections/{id} — Remove connection + unregister tables
"""

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.core.auth import get_current_user
from app.core.database import db
from app.services.auth_service import UserOut
from app.services.credential_encryption import decrypt_password, encrypt_password
from app.tools.external_db_executor import ExternalDBExecutor

logger = logging.getLogger("t2s_analysis")

router = APIRouter(prefix="/api/connections", tags=["connections"])

_executor = ExternalDBExecutor()


async def _ensure_bootstrap():
    """Ensure bootstrap is initialized."""
    from app.bootstrap import bootstrap
    if not bootstrap._initialized:
        await bootstrap.run()
    return bootstrap


class ConnectionRequest(BaseModel):
    display_name: str
    host: str
    port: int = 3306
    database: str
    username: str
    password: str


class ConnectionInfo(BaseModel):
    id: str
    display_name: str
    host: str
    port: int
    database: str
    status: str
    table_count: int = 0
    created_at: str = ""


@router.post("/test")
async def test_connection(req: ConnectionRequest, user: UserOut = Depends(get_current_user)):
    """Test a MySQL connection without saving."""
    await _ensure_bootstrap()
    cfg = {
        "host": req.host, "port": req.port, "database": req.database,
        "username": req.username, "password": req.password,
    }
    try:
        tables = await _executor.test_connection(cfg)
        return {"success": True, "tables": tables, "count": len(tables)}
    except Exception as exc:
        return {"success": False, "error": str(exc)[:200]}


@router.post("")
async def create_connection(req: ConnectionRequest, user: UserOut = Depends(get_current_user)):
    """Save a MySQL connection and register its tables."""
    bootstrap = await _ensure_bootstrap()

    cfg = {
        "host": req.host, "port": req.port, "database": req.database,
        "username": req.username, "password": req.password,
    }

    # Test connection first
    try:
        tables = await _executor.test_connection(cfg)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"连接失败: {str(exc)[:200]}")

    # Introspect tables
    try:
        columns_map = await _executor.introspect_tables(cfg)
    except Exception as exc:
        logger.warning({"event": "introspect_tables_failed", "error": str(exc)[:200]})
        columns_map = {}

    conn_id = str(uuid.uuid4())
    encrypted_pw = encrypt_password(req.password)

    # Persist to MySQL
    await db.execute(
        "INSERT INTO mysql_connections "
        "(id, user_id, display_name, host, port, `database`, username, encrypted_password, status) "
        "VALUES (:id, :uid, :name, :host, :port, :db, :user, :pw, 'active')",
        {
            "id": conn_id, "uid": user.id, "name": req.display_name,
            "host": req.host, "port": req.port, "db": req.database,
            "user": req.username, "pw": encrypted_pw,
        },
    )

    # Register tables in the registry
    registered = []
    for table_name in tables:
        full_name = f"mysql_{conn_id[:8]}_{table_name}"
        columns_meta = columns_map.get(table_name, [])
        bootstrap.registry.register(
            table_name=full_name,
            display_name=f"{req.display_name}.{table_name}",
            source_type="mysql",
            user_id=user.id,
            columns_meta=columns_meta,
        )
        # Store mapping for executor routing
        bootstrap.registry._index[full_name]["connection_id"] = conn_id
        bootstrap.registry._index[full_name]["external_table"] = table_name
        registered.append(full_name)

    return {
        "id": conn_id,
        "display_name": req.display_name,
        "tables": tables,
        "registered_tables": registered,
        "count": len(tables),
    }


@router.get("")
async def list_connections(user: UserOut = Depends(get_current_user)):
    """List user's MySQL connections."""
    bootstrap = await _ensure_bootstrap()
    rows = await db.execute(
        "SELECT id, display_name, host, port, `database`, status, created_at "
        "FROM mysql_connections WHERE user_id = :uid ORDER BY created_at DESC",
        {"uid": user.id},
    )
    connections = []
    for r in rows:
        count = sum(
            1 for m in bootstrap.registry._index.values()
            if m.get("connection_id") == r["id"]
        )
        connections.append({
            "id": r["id"],
            "display_name": r["display_name"],
            "host": r["host"],
            "port": r["port"],
            "database": r["database"],
            "status": r["status"],
            "table_count": count,
            "created_at": str(r.get("created_at", "")),
        })
    return {"connections": connections}


@router.delete("/{connection_id}")
async def delete_connection(connection_id: str, user: UserOut = Depends(get_current_user)):
    """Delete a connection and unregister its tables."""
    bootstrap = await _ensure_bootstrap()

    rows = await db.execute(
        "SELECT id, host, port, `database`, username, encrypted_password "
        "FROM mysql_connections WHERE id = :id AND user_id = :uid",
        {"id": connection_id, "uid": user.id},
    )
    if not rows:
        raise HTTPException(status_code=404, detail="Connection not found")

    row = rows[0]

    # Unregister all tables for this connection
    to_remove = [
        name for name, meta in bootstrap.registry._index.items()
        if meta.get("connection_id") == connection_id
    ]
    for name in to_remove:
        bootstrap.registry.unregister(name)

    # Invalidate cached engine
    try:
        pw = decrypt_password(row["encrypted_password"])
        _executor.invalidate({
            "host": row["host"], "port": row["port"],
            "database": row["database"], "username": row["username"], "password": pw,
        })
    except Exception as exc:
        logger.warning({"event": "invalidate_engine_failed", "error": str(exc)[:200]})

    # Delete from MySQL
    await db.execute("DELETE FROM mysql_connections WHERE id = :id", {"id": connection_id})

    return {"ok": True, "deleted": connection_id, "tables_removed": len(to_remove)}
