"""Quick verification script for Database connectivity.

Usage:
    set PYTHONPATH=backend
    python backend/scripts/check_database.py

Expected output:
    [{'1': 1}]
    True
"""

import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.core.database import db  # noqa: E402


async def main():
    db.init()
    result = await db.execute("SELECT 1")
    print(result)
    healthy = await db.health()
    print(healthy)
    await db.close()


if __name__ == "__main__":
    asyncio.run(main())
