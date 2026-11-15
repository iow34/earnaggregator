import asyncio
import time
from typing import Optional
from app.utils.logger import logger


class TokenBucket:
    def __init__(self, max_tokens: int, refill_rate: float):
        self.max_tokens = max_tokens
        self.refill_rate = refill_rate
        self.tokens = float(max_tokens)
        self.last_refill_time = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self, tokens: int = 1, timeout: Optional[float] = None) -> bool:
        if tokens > self.max_tokens:
            raise ValueError(f"Запитано {tokens} токенів, але max_tokens={self.max_tokens}")

        start_time = time.monotonic()

        async with self._lock:
            while True:
                await self._refill()

                if self.tokens >= tokens:
                    self.tokens -= tokens
                    logger.debug(
                        f"[TokenBucket] Отримано {tokens} токенів. Залишилось: {self.tokens:.2f}"
                    )
                    return True

                if timeout is not None:
                    elapsed = time.monotonic() - start_time
                    if elapsed >= timeout:
                        logger.warning(
                            f"[TokenBucket] Timeout після {elapsed:.2f}s. Недостатньо токенів: {self.tokens:.2f}/{tokens}"
                        )
                        return False

                tokens_needed = tokens - self.tokens
                wait_time = tokens_needed / self.refill_rate

                logger.debug(
                    f"[TokenBucket] Очікування {wait_time:.3f}s для {tokens_needed:.2f} токенів"
                )
                await asyncio.sleep(wait_time)

    async def _refill(self):
        now = time.monotonic()
        elapsed = now - self.last_refill_time

        new_tokens = elapsed * self.refill_rate

        if new_tokens > 0:
            self.tokens = min(self.max_tokens, self.tokens + new_tokens)
            self.last_refill_time = now
            logger.debug(
                f"[TokenBucket] Поповнено {new_tokens:.2f} токенів. Всього: {self.tokens:.2f}"
            )

    def get_available_tokens(self) -> float:
        return self.tokens

    def reset(self):
        self.tokens = float(self.max_tokens)
        self.last_refill_time = time.monotonic()
        logger.info(f"[TokenBucket] Скинуто до {self.max_tokens} токенів")


class RateLimiter:
    def __init__(self):
        self._buckets: dict[str, TokenBucket] = {}

    def create_limiter(self, name: str, max_requests: int, per_seconds: float = 1.0) -> TokenBucket:
        refill_rate = max_requests / per_seconds
        bucket = TokenBucket(max_tokens=max_requests, refill_rate=refill_rate)
        self._buckets[name] = bucket

        logger.info(f"[RateLimiter] Створено limiter '{name}': {max_requests} req/{per_seconds}s")
        return bucket

    def get_limiter(self, name: str) -> Optional[TokenBucket]:
        return self._buckets.get(name)

    async def acquire(self, name: str, tokens: int = 1, timeout: Optional[float] = None) -> bool:
        bucket = self._buckets.get(name)
        if bucket is None:
            raise ValueError(f"Rate limiter '{name}' не знайдено")

        return await bucket.acquire(tokens, timeout)


rate_limiter = RateLimiter()
