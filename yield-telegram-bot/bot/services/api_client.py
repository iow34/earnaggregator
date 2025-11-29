"""
HTTP клієнт для запитів до Data Service API.
"""

import asyncio
import hashlib
import json
import time
from typing import Any, Dict, List, Optional
from functools import wraps

import httpx
from bot.config import settings
from bot.utils.logger import logger
from bot.utils.circuit_breaker import api_circuit_breaker
from bot.utils.metrics import metrics_collector, API_CACHE_HITS


def ttl_cache(ttl_seconds: int):
    """
    Декоратор для TTL кешування результатів функцій.

    Args:
        ttl_seconds: Час життя кешу в секундах
    """
    def decorator(func):
        cache = {}

        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Створюємо ключ кешу на основі функції та аргументів
            key_data = {
                'func': func.__name__,
                'args': args[1:],  # Пропускаємо self
                'kwargs': kwargs
            }
            key = hashlib.md5(json.dumps(key_data, sort_keys=True).encode()).hexdigest()

            # Перевіряємо кеш
            if key in cache:
                cached_result, timestamp = cache[key]
                if time.time() - timestamp < ttl_seconds:
                    logger.debug(f"🎯 API cache hit: {func.__name__}")
                    API_CACHE_HITS.labels(endpoint=func.__name__).inc()
                    return cached_result
                else:
                    # Кеш протух - видаляємо
                    del cache[key]

            # Виконуємо функцію
            result = await func(*args, **kwargs)

            # Кешуємо результат
            cache[key] = (result, time.time())
            logger.debug(f"💾 API cache set: {func.__name__} (TTL: {ttl_seconds}s)")

            return result

        return wrapper
    return decorator


class APIClient:
    def __init__(
        self,
        base_url: str | None = None,
        timeout: float | None = None,
        max_retries: int = 3,
        backoff_factor: float = 1.5
    ) -> None:
        self._base_url = base_url or str(settings.DATA_SERVICE_URL)
        self._timeout = timeout or settings.REQUEST_TIMEOUT
        self._max_retries = max_retries
        self._backoff_factor = backoff_factor
        self._client = httpx.AsyncClient(base_url=self._base_url, timeout=self._timeout)

    async def close(self) -> None:
        await self._client.aclose()

    async def _get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Виконати GET запит з circuit breaker захистом."""

        async def _make_request():
            last_exception = None

            for attempt in range(self._max_retries + 1):
                try:
                    resp = await self._client.get(path, params=params)
                    resp.raise_for_status()
                    return resp.json()
                except httpx.TimeoutException as e:
                    last_exception = e
                    if attempt < self._max_retries:
                        delay = self._backoff_factor ** attempt
                        logger.warning(f"API timeout (attempt {attempt + 1}/{self._max_retries + 1}), retrying in {delay:.1f}s",
                                     extra={"path": path, "params": params, "attempt": attempt + 1})
                        await asyncio.sleep(delay)
                        continue
                    logger.error("API timeout (final attempt)", extra={"path": path, "params": params, "attempts": attempt + 1})
                except httpx.HTTPStatusError as e:
                    # Retry on server errors (5xx) and rate limits (429)
                    if e.response.status_code >= 500 or e.response.status_code == 429:
                        last_exception = e
                        if attempt < self._max_retries:
                            delay = self._backoff_factor ** attempt
                            logger.warning(f"API server error {e.response.status_code} (attempt {attempt + 1}/{self._max_retries + 1}), retrying in {delay:.1f}s",
                                         extra={"path": path, "status": e.response.status_code, "attempt": attempt + 1})
                            await asyncio.sleep(delay)
                            continue
                    # Don't retry on client errors (4xx except 429)
                    logger.error(f"API client error {e.response.status_code}",
                               extra={"path": path, "status": e.response.status_code})
                    raise
                except Exception as e:
                    last_exception = e
                    if attempt < self._max_retries:
                        delay = self._backoff_factor ** attempt
                        logger.warning(f"API error (attempt {attempt + 1}/{self._max_retries + 1}), retrying in {delay:.1f}s: {e}",
                                     extra={"path": path, "attempt": attempt + 1})
                        await asyncio.sleep(delay)
                        continue
                    logger.error(f"API error (final attempt): {e}", extra={"path": path, "attempts": attempt + 1})

            # If we get here, all retries failed
            if last_exception:
                raise last_exception
            raise Exception("API request failed after all retries")

        # Виклик через circuit breaker
        return await api_circuit_breaker.call(_make_request)

    @ttl_cache(ttl_seconds=120)  # 2 хвилини кешування для окремих символів
    async def get_yield_by_symbol(self, symbol: str, limit: Optional[int] = None) -> Dict[str, Any]:
        params = {"limit": limit} if limit is not None else None
        return await self._get(f"/api/v1/yield/{symbol}", params=params)

    async def get_multiple_yields(self, symbols: List[str], limit: Optional[int] = None) -> Dict[str, Any]:
        """
        Отримати yield продукти для множини символів (батч-запит).

        Args:
            symbols: Список символів монет
            limit: Кількість продуктів для кожного символу

        Returns:
            Dict з продуктами для кожного символу
        """
        params = {"symbols": ",".join(symbols), "batch": "true"}
        if limit is not None:
            params["limit"] = limit
        return await self._get("/api/v1/yield/batch", params=params)

    async def get_top(self, limit: int = 20) -> Dict[str, Any]:
        return await self._get("/api/v1/top", params={"limit": limit})

    @ttl_cache(ttl_seconds=600)  # 10 хвилин кешування для даних бірж (збільшено для кращої продуктивності)
    async def get_exchanges(self, exchange: str, symbol: Optional[str] = None, limit: Optional[int] = None) -> Dict[str, Any]:
        params: Dict[str, Any] = {"exchange": exchange}
        if symbol:
            params["symbol"] = symbol
        if limit is not None:
            params["limit"] = limit
        return await self._get("/api/v1/exchanges", params=params)

    async def get_exchanges_popular(self, exchange: str, limit: Optional[int] = None) -> Dict[str, Any]:
        """
        Отримати продукти конкретної біржі відсортовані за популярністю.

        Args:
            exchange: Назва біржі (binance, bybit)
            limit: Кількість продуктів для повернення

        Returns:
            Dict з продуктами відсортованими за популярністю
        """
        params: Dict[str, Any] = {}
        if limit is not None:
            params["limit"] = limit
        return await self._get(f"/api/v1/exchanges/{exchange}/popular", params=params)

    async def get_products_popular(self, limit: Optional[int] = None, offset: Optional[int] = None) -> Dict[str, Any]:
        """
        Отримати всі продукти відсортовані за популярністю.

        Args:
            limit: Кількість продуктів для повернення
            offset: Зміщення для пагінації

        Returns:
            Dict з продуктами відсортованими за популярністю
        """
        params: Dict[str, Any] = {}
        if limit is not None:
            params["limit"] = limit
        if offset is not None:
            params["offset"] = offset
        return await self._get("/api/v1/products/popular", params=params)

    async def get_okx_products(self, limit: Optional[int] = None) -> Dict[str, Any]:
        """Отримати продукти OKX."""
        params = {}
        if limit is not None:
            params["limit"] = limit
        return await self._get("/api/v1/okx/products", params=params)

    async def get_okx_popular(self, limit: Optional[int] = None) -> Dict[str, Any]:
        """Отримати популярні продукти OKX."""
        params = {}
        if limit is not None:
            params["limit"] = limit
        return await self._get("/api/v1/exchanges/okx/popular", params=params)

    async def get_okx_by_symbol(self, symbol: str, limit: Optional[int] = None) -> Dict[str, Any]:
        """Отримати продукти OKX для конкретного символу."""
        params: Dict[str, Any] = {"exchange": "okx"}
        if limit is not None:
            params["limit"] = limit
        return await self._get(f"/api/v1/yield/{symbol}", params=params)

    async def get_gate_products(self, limit: Optional[int] = None) -> Dict[str, Any]:
        """Отримати продукти Gate.io."""
        params = {}
        if limit is not None:
            params["limit"] = limit
        return await self._get("/api/v1/gate/products", params=params)

    async def get_gate_popular(self, limit: Optional[int] = None) -> Dict[str, Any]:
        """Отримати популярні продукти Gate.io."""
        params = {}
        if limit is not None:
            params["limit"] = limit
        return await self._get("/api/v1/exchanges/gate/popular", params=params)

    async def get_gate_by_symbol(self, symbol: str, limit: Optional[int] = None) -> Dict[str, Any]:
        """Отримати продукти Gate.io для конкретного символу."""
        params: Dict[str, Any] = {"exchange": "gate"}
        if limit is not None:
            params["limit"] = limit
        return await self._get(f"/api/v1/yield/{symbol}", params=params)

    async def get_kucoin_products(self, limit: Optional[int] = None) -> Dict[str, Any]:
        """Отримати продукти KuCoin."""
        params = {"exchange": "kucoin"}
        if limit is not None:
            params["limit"] = limit
        return await self._get("/api/v1/exchanges", params=params)

    async def get_all_products(
        self,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        symbol: Optional[str] = None,
        provider: Optional[str] = None,
        sort_by: Optional[str] = "popularity",
        lock_period_days: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Отримати всі продукти з усіх бірж.

        Args:
            limit: Кількість продуктів
            offset: Зміщення для пагінації
            symbol: Фільтр по символу
            provider: Фільтр по провайдеру
            sort_by: Сортування (popularity за замовчуванням, apy_desc, apy_asc)
            lock_period_days: Фільтр по періоду блокування (0 = Flexible)

        Returns:
            Dict з продуктами
        """
        params: Dict[str, Any] = {}
        if limit is not None:
            params["limit"] = limit
        if offset is not None:
            params["offset"] = offset
        if symbol:
            params["symbol"] = symbol
        if provider:
            params["provider"] = provider
        if sort_by:
            params["sort_by"] = sort_by
        if lock_period_days is not None:
            params["lock_period_days"] = lock_period_days
        return await self._get("/api/v1/products", params=params)

    async def get_database_stats(self) -> Dict[str, Any]:
        """
        Отримати статистику бази даних.

        Returns:
            Dict зі статистикою БД
        """
        return await self._get("/api/v1/stats")

    async def get_kraken_products(
        self,
        limit: Optional[int] = 50,
        symbol: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Отримати продукти з Kraken біржі.

        Args:
            limit: Кількість продуктів
            symbol: Фільтр по символу

        Returns:
            Dict з продуктами Kraken
        """
        params: Dict[str, Any] = {}
        if limit is not None:
            params["limit"] = limit
        if symbol:
            params["symbol"] = symbol

        return await self._get("/api/v1/exchanges", params={"exchange": "kraken", **params})

    @ttl_cache(ttl_seconds=900)  # 15 хвилин кешування
    async def get_trending_coins(self) -> Dict[str, Any]:
        """
        Отримати trending cryptocurrencies з CoinGecko.

        Returns:
            Dict з trending монетами
        """
        return await self._get("/api/v1/coingecko/trending")

    @ttl_cache(ttl_seconds=900)  # 15 хвилин кешування
    async def get_trending_stats(self) -> Dict[str, Any]:
        """
        Отримати статистику trending cryptocurrencies.

        Returns:
            Dict зі статистикою trending
        """
        return await self._get("/api/v1/coingecko/trending-stats")

    @ttl_cache(ttl_seconds=60)  # 1 хвилина кешування для priority products (частіше оновлення)
    async def get_priority_products(self, exchange: str) -> Dict[str, Any]:
        """
        Отримати основні продукти (BTC, ETH, SOL, USDT) для біржі.
        
        Завжди повертає 4 продукти в правильному порядку: BTC, ETH, SOL, USDT.
        Якщо продукт не знайдено - повертає з APY=0.0.
        
        Args:
            exchange: Назва біржі (binance, bybit, okx, mexc, bitmart, gate, bitget, kraken, kucoin, htx)
            
        Returns:
            Dict з продуктами в порядку BTC, ETH, SOL, USDT
        """
        return await self._get(f"/api/v1/priority-products/{exchange}")

    async def health(self) -> Dict[str, Any]:
        return await self._get("/api/v1/health")
