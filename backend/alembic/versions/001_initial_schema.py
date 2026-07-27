"""Initial schema — all 5 MySQL tables.

Revision ID: 001_initial
Revises: None
Create Date: 2026-07-27

Tables: users, datasets, sessions, messages, mysql_connections
"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "001_initial"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create all 5 MySQL tables."""

    # ── users ────────────────────────────────────────────
    op.execute(
        "CREATE TABLE IF NOT EXISTS users ("
        "  id VARCHAR(36) PRIMARY KEY,"
        "  username VARCHAR(64) NOT NULL UNIQUE,"
        "  password_hash VARCHAR(255) NOT NULL,"
        "  display_name VARCHAR(128),"
        "  created_at DATETIME DEFAULT CURRENT_TIMESTAMP"
        ")"
    )

    # ── datasets ─────────────────────────────────────────
    op.execute(
        "CREATE TABLE IF NOT EXISTS datasets ("
        "  id VARCHAR(36) PRIMARY KEY,"
        "  name VARCHAR(255) NOT NULL,"
        "  source_type VARCHAR(32) NOT NULL,"
        "  status VARCHAR(32) DEFAULT 'ready',"
        "  table_name VARCHAR(128) NOT NULL UNIQUE,"
        "  session_id VARCHAR(64),"
        "  user_id VARCHAR(36),"
        "  row_count INT DEFAULT 0,"
        "  column_count INT DEFAULT 0,"
        "  columns_meta JSON,"
        "  profile_meta JSON,"
        "  original_file VARCHAR(500),"
        "  file_size_bytes BIGINT DEFAULT 0,"
        "  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,"
        "  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,"
        "  INDEX idx_datasets_session (session_id),"
        "  INDEX idx_datasets_status (status),"
        "  INDEX idx_datasets_source (source_type),"
        "  INDEX idx_datasets_user (user_id)"
        ")"
    )

    # ── sessions ─────────────────────────────────────────
    op.execute(
        "CREATE TABLE IF NOT EXISTS sessions ("
        "  id VARCHAR(64) PRIMARY KEY,"
        "  title VARCHAR(255) NOT NULL DEFAULT '新对话',"
        "  user_id VARCHAR(36),"
        "  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,"
        "  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,"
        "  INDEX idx_sessions_user (user_id)"
        ")"
    )

    # ── messages ─────────────────────────────────────────
    op.execute(
        "CREATE TABLE IF NOT EXISTS messages ("
        "  id INT AUTO_INCREMENT PRIMARY KEY,"
        "  session_id VARCHAR(64) NOT NULL,"
        "  role VARCHAR(16) NOT NULL,"
        "  content TEXT,"
        "  sql_text TEXT,"
        "  chart_type VARCHAR(32),"
        "  echarts_option JSON,"
        "  insight TEXT,"
        "  `columns` JSON,"
        "  rows_data JSON,"
        "  evidence JSON,"
        "  elapsed_ms FLOAT DEFAULT 0,"
        "  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,"
        "  INDEX idx_messages_session (session_id)"
        ")"
    )

    # ── mysql_connections ────────────────────────────────
    op.execute(
        "CREATE TABLE IF NOT EXISTS mysql_connections ("
        "  id VARCHAR(36) PRIMARY KEY,"
        "  user_id VARCHAR(36) NOT NULL,"
        "  display_name VARCHAR(128),"
        "  host VARCHAR(255) NOT NULL,"
        "  port INT DEFAULT 3306,"
        "  `database` VARCHAR(128) NOT NULL,"
        "  username VARCHAR(128) NOT NULL,"
        "  encrypted_password VARCHAR(512) NOT NULL,"
        "  status VARCHAR(32) DEFAULT 'active',"
        "  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,"
        "  INDEX idx_conn_user (user_id)"
        ")"
    )


def downgrade() -> None:
    """Drop all 5 MySQL tables."""
    op.execute("DROP TABLE IF EXISTS mysql_connections")
    op.execute("DROP TABLE IF EXISTS messages")
    op.execute("DROP TABLE IF EXISTS sessions")
    op.execute("DROP TABLE IF EXISTS datasets")
    op.execute("DROP TABLE IF EXISTS users")
