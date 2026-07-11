"""Tests for Database and RedisClient connectivity."""

import pytest

from app.core.database import db as _db
from app.core.redis import redis_client as _redis


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


# ── Redis tests ───────────────────────────────────────

@pytest.fixture(scope="module")
def redis():
    _redis.init()
    yield _redis


@pytest.mark.asyncio
async def test_redis_set_get(redis):
    await redis.set("pytest:key", "pytest_value", expire=60)
    val = await redis.get("pytest:key")
    assert val == "pytest_value"


@pytest.mark.asyncio
async def test_redis_exists(redis):
    await redis.set("pytest:exists", "1", expire=60)
    assert await redis.exists("pytest:exists") is True
    await redis.delete("pytest:exists")
    assert await redis.exists("pytest:exists") is False


@pytest.mark.asyncio
async def test_redis_delete(redis):
    await redis.set("pytest:del", "to_delete", expire=60)
    assert await redis.delete("pytest:del") is True
    assert await redis.delete("pytest:del") is False
