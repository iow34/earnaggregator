"""Exercise both service schemas against a disposable PostgreSQL database."""

import os
from pathlib import Path
import sys
import hashlib

import pytest
from sqlalchemy import select
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

for service in ("yield-data-service", "yield-telegram-bot"):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / service))
from app.db.models import Base as DataBase, YieldProductDB
from bot.db.models import Base as BotBase, AdminUser
from bot.db.crud import create_admin_user, get_admin_by_api_key
from bot.broadcasts.auth import AdminAuthService


@pytest.mark.asyncio
async def test_fresh_schemas_catalogue_and_hashed_admin_keys():
    url = os.getenv("TEST_DATABASE_URL")
    if not url:
        pytest.skip("Set TEST_DATABASE_URL to a disposable local PostgreSQL database")
    parsed = make_url(url)
    assert parsed.host in {"localhost", "127.0.0.1", "postgres"}
    assert parsed.database and parsed.database.endswith("_test")
    engine = create_async_engine(url)
    try:
        async with engine.begin() as conn:
            await conn.run_sync(DataBase.metadata.create_all)
            await conn.run_sync(BotBase.metadata.create_all)
        async with async_sessionmaker(engine, expire_on_commit=False)() as session:
            item = YieldProductDB(
                id="integration-btc",
                symbol="BTC",
                name="Bitcoin Flexible",
                provider="Binance",
                apy=2.4,
            )
            session.add(item)
            auth = AdminAuthService()
            key = auth.issue_api_key()
            await create_admin_user(
                session,
                email="integration@example.com",
                password_hash=auth.hash_password("integration-password"),
                api_key=key,
                role="owner",
            )
            await session.commit()
            stored = (
                await session.execute(select(YieldProductDB).where(YieldProductDB.id == item.id))
            ).scalar_one()
            assert stored.apy == 2.4
            admin = await get_admin_by_api_key(session, key)
            assert isinstance(admin, AdminUser)
            assert admin.api_key == hashlib.sha256(key.encode()).hexdigest()
            assert admin.api_key != key
            assert await get_admin_by_api_key(session, "wrong-key") is None
    finally:
        async with engine.begin() as conn:
            await conn.run_sync(BotBase.metadata.drop_all)
            await conn.run_sync(DataBase.metadata.drop_all)
        await engine.dispose()


def test_index_names_are_unique_across_both_service_schemas():
    from collections import Counter

    names = Counter(
        index.name
        for base in (DataBase, BotBase)
        for table in base.metadata.tables.values()
        for index in table.indexes
    )
    assert all(count == 1 for count in names.values())
