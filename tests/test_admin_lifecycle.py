from unittest.mock import AsyncMock

import pytest
from bot.admin_app import lifespan, app, db_manager


@pytest.mark.asyncio
async def test_admin_database_is_closed_after_shutdown(monkeypatch):
    initialize = AsyncMock(return_value=True)
    close = AsyncMock()
    monkeypatch.setattr(db_manager, "initialize", initialize)
    monkeypatch.setattr(db_manager, "close_engine", close)
    async with lifespan(app):
        initialize.assert_awaited_once()
        close.assert_not_awaited()
    close.assert_awaited_once()


@pytest.mark.asyncio
async def test_admin_api_refuses_failed_database_startup(monkeypatch):
    monkeypatch.setattr(db_manager, "initialize", AsyncMock(return_value=False))
    with pytest.raises(RuntimeError, match="initialization failed"):
        async with lifespan(app):
            pytest.fail("Application must not start after database failure")
