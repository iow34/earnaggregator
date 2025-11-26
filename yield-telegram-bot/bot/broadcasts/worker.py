"""
Асинхронний worker для обробки ручних розсилок.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import Optional

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError, TelegramRetryAfter
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.broadcasts.queue import BroadcastQueue
from bot.broadcasts.sender import BroadcastSender
from bot.config import settings
from bot.db import crud
from bot.db.database import get_database_session
from bot.db.models import Broadcast, BroadcastRecipient
from bot.utils.logger import logger
from bot.utils.metrics import (
    BROADCAST_MESSAGES_TOTAL,
    BROADCAST_FAILURES_TOTAL,
    BROADCAST_IN_PROGRESS,
)


class BroadcastWorker:
    """Worker який читає чергу та розсилає повідомлення."""

    def __init__(
        self,
        *,
        queue: BroadcastQueue,
        sender: BroadcastSender,
        session_factory=get_database_session,
        rate_delay: float = settings.BROADCAST_RATE_DELAY,
        retry_base_delay: float = settings.BROADCAST_RETRY_BASE_DELAY,
        retry_max_delay: float = settings.BROADCAST_RETRY_MAX_DELAY,
        batch_size: int = 100,
    ) -> None:
        self._queue = queue
        self._sender = sender
        self._session_factory = session_factory
        self._rate_delay = rate_delay
        self._retry_base_delay = retry_base_delay
        self._retry_max_delay = retry_max_delay
        self._batch_size = batch_size
        self._running = False
        self._task: Optional[asyncio.Task] = None

    async def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._run())
        logger.info("Broadcast worker started")

    async def stop(self) -> None:
        self._running = False
        if self._task:
            await self._task
            self._task = None
        logger.info("Broadcast worker stopped")

    async def _run(self) -> None:
        while self._running:
            broadcast_id = await self._queue.dequeue(timeout=5)
            if broadcast_id is None:
                continue
            try:
                await self.process_broadcast(broadcast_id)
            except Exception as exc:
                logger.exception("Broadcast %s failed: %s", broadcast_id, exc)

    async def process_broadcast(self, broadcast_id: int) -> None:
        async with self._session_factory() as session:
            stmt = select(Broadcast).where(Broadcast.id == broadcast_id)
            result = await session.execute(stmt)
            broadcast = result.scalar_one_or_none()
            if not broadcast:
                logger.warning("Broadcast %s not found", broadcast_id)
                return

            if broadcast.status == "cancelled":
                logger.info("Broadcast %s is cancelled, skipping", broadcast_id)
                return

            broadcast.status = "running"
            broadcast.started_at = datetime.now(UTC)
            await session.commit()

            BROADCAST_IN_PROGRESS.inc()
            try:
                while True:
                    stmt = (
                        select(BroadcastRecipient)
                        .where(
                            BroadcastRecipient.broadcast_id == broadcast_id,
                            BroadcastRecipient.status == "pending",
                        )
                        .limit(self._batch_size)
                    )
                    recipients = (await session.execute(stmt)).scalars().all()
                    if not recipients:
                        break
                    for recipient in recipients:
                        await self._process_recipient(session, broadcast, recipient)
                        await asyncio.sleep(self._rate_delay)
            finally:
                BROADCAST_IN_PROGRESS.dec()

            # Якщо немає більше pending, позначаємо як completed
            remaining_stmt = select(BroadcastRecipient.id).where(
                BroadcastRecipient.broadcast_id == broadcast_id,
                BroadcastRecipient.status == "pending",
            )
            remaining = (await session.execute(remaining_stmt)).first()
            if not remaining:
                broadcast.status = "completed"
                broadcast.completed_at = datetime.now(UTC)
                await session.commit()
                await crud.record_broadcast_event(
                    session,
                    broadcast_id=broadcast_id,
                    event_type="completed",
                    admin_id=None,
                    payload={"total_recipients": broadcast.total_recipients},
                )
            else:
                logger.info("Broadcast %s still pending; queued for later", broadcast_id)

    async def _process_recipient(
        self,
        session: AsyncSession,
        broadcast: Broadcast,
        recipient: BroadcastRecipient,
    ) -> None:
        try:
            result = await self._sender.send_message(
                telegram_id=recipient.telegram_id,
                content_payload=broadcast.content_payload,
                content_type=broadcast.content_type,
            )
            recipient.status = "sent"
            recipient.message_id = str(result.message_id)
            recipient.error_code = None
            BROADCAST_MESSAGES_TOTAL.inc()
        except TelegramRetryAfter as exc:
            recipient.status = "pending"
            recipient.error_code = "retry_after"
            delay = exc.retry_after or self._compute_backoff(recipient.attempts + 1)
            await self._queue.enqueue_broadcast(broadcast.id, delay=delay)
        except TelegramAPIError as exc:
            recipient.status = "failed"
            recipient.error_code = exc.message
            BROADCAST_FAILURES_TOTAL.inc()
        except Exception as exc:
            recipient.status = "failed"
            recipient.error_code = type(exc).__name__
            BROADCAST_FAILURES_TOTAL.inc()
            logger.exception("Failed to deliver broadcast %s to %s", broadcast.id, recipient.telegram_id)
        finally:
            recipient.attempts += 1
            recipient.last_attempt_at = datetime.now(UTC)
            await session.commit()

    def _compute_backoff(self, attempt: int) -> float:
        delay = self._retry_base_delay * (2 ** max(0, attempt - 1))
        return min(delay, self._retry_max_delay)


def build_worker(bot: Bot) -> BroadcastWorker:
    queue = BroadcastQueue()
    sender = BroadcastSender(bot)
    return BroadcastWorker(queue=queue, sender=sender)

