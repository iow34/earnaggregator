import time
from typing import Any, Callable, Dict, Awaitable

import redis.asyncio as redis

from aiogram import BaseMiddleware
from aiogram.types import Message

from bot.config import settings
from bot.utils.logger import logger
from bot.utils.metrics import BOT_THROTTLED_TOTAL


class ThrottlingMiddleware(BaseMiddleware):
    def __init__(self, redis_url: str, rate_limit: int = 3, time_window: int = 10):
        self.redis_url = redis_url
        self.rate_limit = rate_limit
        self.time_window = time_window
        self.redis = None

    async def _get_redis(self) -> redis.Redis:
        if self.redis is None:
            self.redis = redis.from_url(self.redis_url)
        return self.redis

    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any],
    ) -> Any:
        if not hasattr(event, "from_user") or not event.from_user:
            return await handler(event, data)

        user_id = event.from_user.id
        key = f"throttle:{user_id}"

        try:
            r = await self._get_redis()
            current_time = int(time.time())

            await r.zadd(key, {str(current_time): current_time})

            await r.zremrangebyscore(key, 0, current_time - self.time_window)

            count = await r.zcard(key)

            if count > self.rate_limit:
                BOT_THROTTLED_TOTAL.labels(user_id=str(user_id)).inc()
                logger.warning(
                    "Заборонено через throttling",
                    extra={
                        "user_id": user_id,
                        "count": count,
                        "rate_limit": self.rate_limit,
                        "time_window": self.time_window,
                    },
                )

                if hasattr(event, "answer"):
                    await event.answer(
                        f"⚠️ Занадто багато повідомлень! "
                        f"Обмеження: {self.rate_limit} повідомлень за {self.time_window} секунд."
                    )
                return

            return await handler(event, data)

        except Exception as e:
            logger.error(f"Помилка в throttling middleware: {e}")

            return await handler(event, data)
