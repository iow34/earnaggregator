"""
Rate Limiter для контролю частоти запитів до зовнішніх API.

Реалізує Token Bucket алгоритм для обмеження кількості запитів за секунду.
"""

import asyncio
import time
from typing import Optional
from app.utils.logger import logger


class TokenBucket:
    """
    Token Bucket алгоритм для rate limiting.
    
    Дозволяє контролювати швидкість запитів до API.
    Кожен запит "споживає" токен. Токени поповнюються з фіксованою швидкістю.
    """

    def __init__(self, max_tokens: int, refill_rate: float):
        """
        Ініціалізує Token Bucket.

        Args:
            max_tokens: Максимальна кількість токенів в bucket
            refill_rate: Швидкість поповнення токенів (токенів за секунду)
        """
        self.max_tokens = max_tokens
        self.refill_rate = refill_rate
        self.tokens = float(max_tokens)
        self.last_refill_time = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self, tokens: int = 1, timeout: Optional[float] = None) -> bool:
        """
        Отримує токени з bucket (блокуючий виклик).

        Args:
            tokens: Кількість токенів для отримання
            timeout: Максимальний час очікування в секундах

        Returns:
            bool: True якщо токени отримані, False якщо timeout

        Raises:
            ValueError: Якщо запитано більше токенів ніж max_tokens
        """
        if tokens > self.max_tokens:
            raise ValueError(f"Запитано {tokens} токенів, але max_tokens={self.max_tokens}")

        start_time = time.monotonic()

        async with self._lock:
            while True:
                # Поповнюємо токени
                await self._refill()

                # Перевіряємо чи достатньо токенів
                if self.tokens >= tokens:
                    self.tokens -= tokens
                    logger.debug(f"[TokenBucket] Отримано {tokens} токенів. Залишилось: {self.tokens:.2f}")
                    return True

                # Перевіряємо timeout
                if timeout is not None:
                    elapsed = time.monotonic() - start_time
                    if elapsed >= timeout:
                        logger.warning(f"[TokenBucket] Timeout після {elapsed:.2f}s. Недостатньо токенів: {self.tokens:.2f}/{tokens}")
                        return False

                # Обчислюємо час очікування для наступного токена
                tokens_needed = tokens - self.tokens
                wait_time = tokens_needed / self.refill_rate
                
                logger.debug(f"[TokenBucket] Очікування {wait_time:.3f}s для {tokens_needed:.2f} токенів")
                await asyncio.sleep(wait_time)

    async def _refill(self):
        """Поповнює токени на основі часу з останнього поповнення."""
        now = time.monotonic()
        elapsed = now - self.last_refill_time
        
        # Обчислюємо кількість нових токенів
        new_tokens = elapsed * self.refill_rate
        
        if new_tokens > 0:
            self.tokens = min(self.max_tokens, self.tokens + new_tokens)
            self.last_refill_time = now
            logger.debug(f"[TokenBucket] Поповнено {new_tokens:.2f} токенів. Всього: {self.tokens:.2f}")

    def get_available_tokens(self) -> float:
        """Повертає поточну кількість доступних токенів (без блокування)."""
        return self.tokens

    def reset(self):
        """Скидає bucket до початкового стану."""
        self.tokens = float(self.max_tokens)
        self.last_refill_time = time.monotonic()
        logger.info(f"[TokenBucket] Скинуто до {self.max_tokens} токенів")


class RateLimiter:
    """
    Rate Limiter з підтримкою множинних bucket-ів для різних API.
    
    Дозволяє створювати окремі обмеження для різних сервісів.
    """

    def __init__(self):
        self._buckets: dict[str, TokenBucket] = {}

    def create_limiter(self, name: str, max_requests: int, per_seconds: float = 1.0) -> TokenBucket:
        """
        Створює новий rate limiter для конкретного API.

        Args:
            name: Назва API (наприклад: "okx", "binance")
            max_requests: Максимальна кількість запитів
            per_seconds: За скільки секунд

        Returns:
            TokenBucket: Створений bucket
        """
        refill_rate = max_requests / per_seconds
        bucket = TokenBucket(max_tokens=max_requests, refill_rate=refill_rate)
        self._buckets[name] = bucket
        
        logger.info(f"[RateLimiter] Створено limiter '{name}': {max_requests} req/{per_seconds}s")
        return bucket

    def get_limiter(self, name: str) -> Optional[TokenBucket]:
        """Повертає існуючий limiter за назвою."""
        return self._buckets.get(name)

    async def acquire(self, name: str, tokens: int = 1, timeout: Optional[float] = None) -> bool:
        """
        Отримує токени з конкретного limiter.

        Args:
            name: Назва limiter
            tokens: Кількість токенів
            timeout: Максимальний час очікування

        Returns:
            bool: True якщо токени отримані

        Raises:
            ValueError: Якщо limiter не знайдено
        """
        bucket = self._buckets.get(name)
        if bucket is None:
            raise ValueError(f"Rate limiter '{name}' не знайдено")
        
        return await bucket.acquire(tokens, timeout)


# Глобальний екземпляр rate limiter
rate_limiter = RateLimiter()

