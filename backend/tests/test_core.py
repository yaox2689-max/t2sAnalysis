"""Tests for Database connectivity."""

import pytest

from app.core.database import db as _db

# ── Database tests ────────────────────────────────────

@pytest.fixture(scope="module")
def db():
    _db.init()
    yield _db


@pytest.mark.asyncio
async def test_db_execute_select_one(db):
    result = await db.execute("SELECT 1")
    assert result == [{"1": 1}]


@pytest.mark.asyncio
async def test_db_health(db):
    healthy = await db.health()
    assert healthy is True
