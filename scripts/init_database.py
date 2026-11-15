"""Create a fresh deployment schema. Existing columns are never altered.

Run after reviewing DATABASE_URL, before starting the services. Subsequent
schema upgrades must use reviewed Alembic migrations and a database backup.
"""

import asyncio
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
for folder in (ROOT / "yield-data-service", ROOT / "yield-telegram-bot"):
    sys.path.insert(0, str(folder))

from sqlalchemy.ext.asyncio import create_async_engine
from app.db.models import Base as DataBase
from bot.db.models import Base as BotBase


async def initialize() -> None:
    url = os.environ["DATABASE_URL"].replace("postgresql://", "postgresql+asyncpg://", 1)
    engine = create_async_engine(url)
    try:
        async with engine.begin() as connection:
            await connection.run_sync(DataBase.metadata.create_all)
            await connection.run_sync(BotBase.metadata.create_all)
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(initialize())
