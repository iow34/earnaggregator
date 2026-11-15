from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import Optional

from sqlalchemy import select

from bot.broadcasts.queue import BroadcastQueue
from bot.config import settings
from bot.db import crud
from bot.db.database import get_database_session
from bot.db.models import Broadcast
from bot.utils.logger import logger


class BroadcastScheduler:
    def __init__(
        self,
        *,
        queue: BroadcastQueue,
        session_factory=get_database_session,
        poll_interval: float = settings.BROADCAST_SCHEDULER_INTERVAL,
        batch_size: int = settings.BROADCAST_SCHEDULER_BATCH_SIZE,
    ) -> None:
        self._queue = queue
        self._session_factory = session_factory
        self._interval = poll_interval
        self._batch_size = batch_size
        self._running = False
        self._task: Optional[asyncio.Task] = None

    async def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._run())
        logger.info("Broadcast scheduler started")

    async def stop(self) -> None:
        self._running = False
        if self._task:
            await self._task
            self._task = None
        logger.info("Broadcast scheduler stopped")

    async def _run(self) -> None:
        while self._running:
            try:
                await self._tick()
            except Exception as exc:
                logger.exception("Scheduler tick failed: %s", exc)
            await asyncio.sleep(self._interval)

    async def _tick(self) -> None:
        now = datetime.now(UTC)
        async with self._session_factory() as session:
            stmt = (
                select(Broadcast)
                .where(
                    Broadcast.status == "scheduled",
                    Broadcast.scheduled_at.is_not(None),
                    Broadcast.scheduled_at <= now,
                )
                .limit(self._batch_size)
            )
            result = await session.execute(stmt)
            broadcasts = result.scalars().all()
            if not broadcasts:
                return

            for broadcast in broadcasts:
                broadcast.status = "queued"
            await session.commit()

            for broadcast in broadcasts:
                await crud.record_broadcast_event(
                    session,
                    broadcast_id=broadcast.id,
                    event_type="scheduled_enqueued",
                    admin_id=None,
                    payload={
                        "scheduled_at": broadcast.scheduled_at.isoformat()
                        if broadcast.scheduled_at
                        else None
                    },
                )
                await self._queue.enqueue_broadcast(broadcast.id)
