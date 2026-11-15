from __future__ import annotations

import asyncio
from typing import Optional

import redis.asyncio as aioredis

from bot.config import settings
from bot.utils.logger import logger
from bot.utils.metrics import BROADCAST_QUEUE_DEPTH


class BroadcastQueue:
    def __init__(
        self,
        *,
        redis_url: Optional[str] = None,
        queue_name: Optional[str] = None,
        redis_client: Optional[aioredis.Redis] = None,
    ) -> None:
        self.queue_name = queue_name or settings.BROADCAST_QUEUE_NAME
        self._redis = redis_client or aioredis.from_url(
            redis_url or settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
        )

    async def enqueue_broadcast(self, broadcast_id: int, delay: Optional[float] = None) -> None:
        if delay and delay > 0:
            asyncio.create_task(self._delayed_enqueue(broadcast_id, delay))
            return

        await self._redis.lpush(self.queue_name, broadcast_id)
        await self._update_depth()
        logger.info("Broadcast %s поставлено в чергу", broadcast_id)

    async def _delayed_enqueue(self, broadcast_id: int, delay: float) -> None:
        await asyncio.sleep(delay)
        await self._redis.lpush(self.queue_name, broadcast_id)
        await self._update_depth()
        logger.debug("Broadcast %s повторно поставлено після затримки %s", broadcast_id, delay)

    async def dequeue(self, timeout: int = 5) -> Optional[int]:
        result = await self._redis.brpop(self.queue_name, timeout=timeout)
        if not result:
            return None
        _, value = result
        await self._update_depth()
        return int(value)

    async def size(self) -> int:
        return int(await self._redis.llen(self.queue_name))

    async def _update_depth(self) -> None:
        depth = await self._redis.llen(self.queue_name)
        BROADCAST_QUEUE_DEPTH.set(depth)

    async def close(self) -> None:
        if self._redis:
            await self._redis.close()
