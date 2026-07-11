"""pytest configuration — session-scoped event loop for Windows compat."""

import asyncio
import pytest


@pytest.fixture(scope="session")
def event_loop():
    """Use a single event loop across all tests.

    Required on Windows where aiomysql / redis.asyncio connection
    pools break when the event loop is closed and recreated between
    individual test functions.
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    loop.close()
