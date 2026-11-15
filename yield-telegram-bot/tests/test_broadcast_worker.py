from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from bot.broadcasts.worker import BroadcastWorker
from bot.broadcasts.queue import BroadcastQueue


@pytest.mark.asyncio
async def test_worker_updates_recipient_on_success():
    queue = AsyncMock(spec=BroadcastQueue)
    sender = AsyncMock()
    sender.send_message.return_value = SimpleNamespace(message_id="123")
    worker = BroadcastWorker(queue=queue, sender=sender)

    recipient = SimpleNamespace(id=1, telegram_id=100, attempts=0, status="pending")
    broadcast = SimpleNamespace(id=5, content_type="text", content_payload={"text": "Hello"})
    session = AsyncMock()

    await worker._process_recipient(session, broadcast, recipient)

    assert recipient.status == "sent"
    session.commit.assert_awaited()


def test_backoff_grows_with_attempts():
    queue = AsyncMock(spec=BroadcastQueue)
    sender = AsyncMock()
    worker = BroadcastWorker(queue=queue, sender=sender, retry_base_delay=1.0, retry_max_delay=30.0)

    assert worker._compute_backoff(1) == 1.0
    assert worker._compute_backoff(2) == pytest.approx(2.0)
    assert worker._compute_backoff(10) <= 30.0
