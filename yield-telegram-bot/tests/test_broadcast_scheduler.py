from contextlib import asynccontextmanager
from datetime import datetime, UTC
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from bot.broadcasts.scheduler import BroadcastScheduler


class DummyResult:
    def __init__(self, items):
        self._items = items

    def scalars(self):
        return DummyScalars(self._items)


class DummyScalars:
    def __init__(self, items):
        self._items = items

    def all(self):
        return self._items


@pytest.mark.asyncio
async def test_scheduler_enqueues_ready_broadcasts(monkeypatch):
    queue = AsyncMock()
    broadcast = SimpleNamespace(id=7, status="scheduled", scheduled_at=datetime.now(UTC))
    session = SimpleNamespace(
        execute=AsyncMock(return_value=DummyResult([broadcast])),
        commit=AsyncMock(),
    )

    @asynccontextmanager
    async def fake_session_factory():
        yield session

    record_mock = AsyncMock()
    monkeypatch.setattr("bot.broadcasts.scheduler.crud.record_broadcast_event", record_mock)

    scheduler = BroadcastScheduler(
        queue=queue,
        session_factory=lambda: fake_session_factory(),
        poll_interval=0.01,
        batch_size=10,
    )

    await scheduler._tick()

    session.execute.assert_awaited()
    session.commit.assert_awaited_once()
    queue.enqueue_broadcast.assert_awaited_once_with(7)
    record_mock.assert_awaited()
    assert broadcast.status == "queued"
