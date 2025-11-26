"""
Rate Limiting Middleware для захисту redirect endpoint.

Обмеження: 10 requests/min per IP
Використовує Redis для зберігання лічильників.
"""

import time
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
import redis.asyncio as redis
from typing import Optional

from app.utils.logger import logger


class RateLimiterMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware.
    
    Обмежує кількість запитів з одного IP адреси.
    """
    
    def __init__(
        self,
        app: ASGIApp,
        redis_url: str,
        rate_limit: int = 10,  # Запитів
        time_window: int = 60,  # Секунд
        endpoints: Optional[list] = None
    ):
        """
        Ініціалізація rate limiter.
        
        Args:
            app: ASGI додаток
            redis_url: URL для підключення до Redis
            rate_limit: Максимальна кількість запитів
            time_window: Часове вікно в секундах
            endpoints: Список endpoints для обмеження (None = всі)
        """
        super().__init__(app)
        self.redis_url = redis_url
        self.rate_limit = rate_limit
        self.time_window = time_window
        self.endpoints = endpoints or ['/ref']  # За замовчуванням тільки /ref
        self.redis_client: Optional[redis.Redis] = None
        
    async def init_redis(self):
        """Ініціалізувати Redis клієнт."""
        if not self.redis_client:
            try:
                self.redis_client = redis.from_url(
                    self.redis_url,
                    decode_responses=True
                )
                await self.redis_client.ping()
                logger.info("✅ RateLimiter Redis ініціалізовано")
            except Exception as e:
                logger.error(f"❌ Помилка ініціалізації Redis для rate limiter: {e}")
                self.redis_client = None
    
    async def dispatch(self, request: Request, call_next):
        """Обробити запит з rate limiting."""
        
        # Перевірити чи потрібно обмежувати цей endpoint
        path = request.url.path
        if not any(path.startswith(endpoint) for endpoint in self.endpoints):
            # Не обмежуємо цей endpoint
            return await call_next(request)
        
        # Ініціалізувати Redis якщо потрібно
        if not self.redis_client:
            await self.init_redis()
        
        # Якщо Redis недоступний - пропускаємо rate limiting
        if not self.redis_client:
            logger.warning("⚠️ Rate limiter: Redis недоступний, пропускаємо обмеження")
            return await call_next(request)
        
        # Отримати IP адресу
        client_ip = request.client.host if request.client else "unknown"
        
        # Створити ключ для Redis
        redis_key = f"rate_limit:{client_ip}:{path}"
        
        try:
            # Отримати поточну кількість запитів
            current_requests = await self.redis_client.get(redis_key)
            
            if current_requests is None:
                # Перший запит - створити лічильник
                await self.redis_client.setex(
                    redis_key,
                    self.time_window,
                    1
                )
                logger.debug(f"🔒 Rate limit: {client_ip} -> 1/{self.rate_limit}")
                return await call_next(request)
            
            current_requests = int(current_requests)
            
            if current_requests >= self.rate_limit:
                # Перевищено ліміт
                logger.warning(
                    f"⚠️ Rate limit exceeded: {client_ip} -> {current_requests}/{self.rate_limit} "
                    f"for {path}"
                )
                
                # Логувати suspicious activity
                try:
                    from app.db.database import get_database_session
                    from app.db.tracking_crud import TrackingLogCRUD
                    
                    async with get_database_session() as session:
                        await TrackingLogCRUD.create(
                            session=session,
                            event_type="warning",
                            message=f"Rate limit exceeded from IP {client_ip}",
                            context={
                                "ip": client_ip,
                                "path": path,
                                "requests": current_requests,
                                "limit": self.rate_limit
                            }
                        )
                except Exception as e:
                    logger.error(f"❌ Помилка логування rate limit: {e}")
                
                # Повернути 429 Too Many Requests
                return JSONResponse(
                    status_code=429,
                    content={
                        "error": "Too Many Requests",
                        "message": f"Rate limit exceeded. Max {self.rate_limit} requests per {self.time_window} seconds.",
                        "retry_after": self.time_window
                    },
                    headers={
                        "Retry-After": str(self.time_window),
                        "X-RateLimit-Limit": str(self.rate_limit),
                        "X-RateLimit-Remaining": "0",
                        "X-RateLimit-Reset": str(int(time.time()) + self.time_window)
                    }
                )
            
            # Інкремент лічильника
            await self.redis_client.incr(redis_key)
            remaining = self.rate_limit - current_requests - 1
            
            logger.debug(f"🔒 Rate limit: {client_ip} -> {current_requests + 1}/{self.rate_limit}")
            
            # Виконати запит
            response = await call_next(request)
            
            # Додати rate limit headers
            response.headers["X-RateLimit-Limit"] = str(self.rate_limit)
            response.headers["X-RateLimit-Remaining"] = str(max(0, remaining))
            response.headers["X-RateLimit-Reset"] = str(int(time.time()) + self.time_window)
            
            return response
            
        except Exception as e:
            logger.error(f"❌ Помилка rate limiter: {e}")
            # При помилці - дозволяємо запит
            return await call_next(request)
    
    async def close(self):
        """Закрити з'єднання з Redis."""
        if self.redis_client:
            await self.redis_client.close()


# Утиліта для швидкого створення middleware
def create_rate_limiter(
    redis_url: str,
    rate_limit: int = 10,
    time_window: int = 60,
    endpoints: Optional[list] = None
) -> RateLimiterMiddleware:
    """
    Створити rate limiter middleware.
    
    Args:
        redis_url: URL Redis
        rate_limit: Максимальна кількість запитів
        time_window: Часове вікно в секундах
        endpoints: Список endpoints для обмеження
        
    Returns:
        RateLimiterMiddleware
    """
    return lambda app: RateLimiterMiddleware(
        app,
        redis_url=redis_url,
        rate_limit=rate_limit,
        time_window=time_window,
        endpoints=endpoints
    )

