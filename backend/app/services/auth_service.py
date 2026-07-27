"""Auth service — user registration, login, JWT token management."""

import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
from jose import JWTError, jwt
from pydantic import BaseModel

from app.core.config import settings
from app.core.database import db

logger = logging.getLogger("t2s_analysis")


def _ensure_db() -> None:
    """Ensure database is initialized (lazy init on first auth call)."""
    if not db.is_initialized:
        db.init()


async def _ensure_users_table() -> None:
    """Create users table if it doesn't exist (idempotent)."""
    from app.bootstrap import bootstrap
    if not bootstrap._initialized:
        await bootstrap.run()
    elif not db.is_initialized:
        db.init()
    # Fallback: try creating table directly if bootstrap somehow skipped it
    try:
        await db.execute(
            "CREATE TABLE IF NOT EXISTS users ("
            "  id VARCHAR(36) PRIMARY KEY,"
            "  username VARCHAR(64) NOT NULL UNIQUE,"
            "  password_hash VARCHAR(255) NOT NULL,"
            "  display_name VARCHAR(128),"
            "  created_at DATETIME DEFAULT CURRENT_TIMESTAMP"
            ")"
        )
    except Exception as exc:
        logger.warning({"event": "ensure_users_table_failed", "error": str(exc)[:200]})


def _hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def _verify_password(password: str, hashed: str) -> bool:
    """Verify a password against its bcrypt hash."""
    return bcrypt.checkpw(password.encode(), hashed.encode())


class UserOut(BaseModel):
    """Public user info (no password)."""

    id: str
    username: str
    display_name: Optional[str] = None


class AuthService:
    """User registration, authentication, JWT management."""

    async def register(self, username: str, password: str, display_name: str = "") -> UserOut:
        """Register a new user. Raises ValueError if username taken."""
        await _ensure_users_table()
        existing = await db.execute(
            "SELECT id FROM users WHERE username = :u", {"u": username}
        )
        if existing:
            raise ValueError("用户名已存在")

        user_id = str(uuid.uuid4())
        password_hash = _hash_password(password)
        await db.execute(
            "INSERT INTO users (id, username, password_hash, display_name) "
            "VALUES (:id, :u, :h, :d)",
            {"id": user_id, "u": username, "h": password_hash, "d": display_name or username},
        )
        return UserOut(id=user_id, username=username, display_name=display_name or username)

    async def authenticate(self, username: str, password: str) -> Optional[UserOut]:
        """Verify credentials. Returns UserOut on success, None on failure."""
        await _ensure_users_table()
        rows = await db.execute(
            "SELECT id, username, password_hash, display_name FROM users WHERE username = :u",
            {"u": username},
        )
        if not rows:
            return None
        row = rows[0]
        if not _verify_password(password, row["password_hash"]):
            return None
        return UserOut(id=row["id"], username=row["username"], display_name=row["display_name"])

    @staticmethod
    def create_token(user_id: str) -> str:
        """Create a JWT access token."""
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
        payload = {"sub": user_id, "exp": expire}
        return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

    @staticmethod
    def decode_token(token: str) -> Optional[str]:
        """Decode JWT and return user_id, or None if invalid/expired."""
        try:
            payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
            return payload.get("sub")
        except JWTError:
            return None

    async def get_user(self, user_id: str) -> Optional[UserOut]:
        """Look up user by ID."""
        await _ensure_users_table()
        rows = await db.execute(
            "SELECT id, username, display_name FROM users WHERE id = :id",
            {"id": user_id},
        )
        if not rows:
            return None
        row = rows[0]
        return UserOut(id=row["id"], username=row["username"], display_name=row["display_name"])


# Module-level singleton
auth_service = AuthService()
