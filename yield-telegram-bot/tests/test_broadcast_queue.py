import asyncio
from unittest.mock import AsyncMock

import pytest

from bot.broadcasts.queue import BroadcastQueue


@pytest.mark.asyncio
async def test_enqueue_broadcast_pushes_id():
    redis = AsyncMock()
    queue = BroadcastQueue(redis_client=redis, queue_name="broadcasts")

    await queue.enqueue_broadcast(42)

    redis.lpush.assert_called_once_with("broadcasts", 42)


@pytest.mark.asyncio
async def test_enqueue_with_delay_schedules_task():
    redis = AsyncMock()
    queue = BroadcastQueue(redis_client=redis, queue_name="broadcasts")

    await queue.enqueue_broadcast(99, delay=0.01)
    await asyncio.sleep(0.05)

    redis.lpush.assert_called_once_with("broadcasts", 99)


@pytest.mark.asyncio
async def test_dequeue_handles_timeout():
    redis = AsyncMock()
    redis.brpop.return_value = None
    queue = BroadcastQueue(redis_client=redis, queue_name="broadcasts")

    result = await queue.dequeue(timeout=0)

    assert result is None
    redis.brpop.assert_called_once_with("broadcasts", timeout=0)
