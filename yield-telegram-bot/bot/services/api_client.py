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
    def decorator(func):
        cache = {}

        @wraps(func)
        async def wrapper(*args, **kwargs):

            key_data = {"func": func.__name__, "args": args[1:], "kwargs": kwargs}
            key = hashlib.md5(json.dumps(key_data, sort_keys=True).encode()).hexdigest()

            if key in cache:
                cached_result, timestamp = cache[key]
                if time.time() - timestamp < ttl_seconds:
                    logger.debug(f"🎯 API cache hit: {func.__name__}")
                    API_CACHE_HITS.labels(endpoint=func.__name__).inc()
                    return cached_result
                else:
                    del cache[key]

            result = await func(*args, **kwargs)

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
        backoff_factor: float = 1.5,
    ) -> None:
        self._base_url = base_url or settings.data_service_url
        self._timeout = timeout or settings.REQUEST_TIMEOUT
        self._max_retries = max_retries
        self._backoff_factor = backoff_factor
        self._client = httpx.AsyncClient(
            headers={"X-Service-API-Key": settings.SERVICE_API_KEY},
            base_url=self._base_url,
            timeout=self._timeout,
        )

    async def close(self) -> None:
        await self._client.aclose()

    async def _get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:

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
                        delay = self._backoff_factor**attempt
                        logger.warning(
                            f"API timeout (attempt {attempt + 1}/{self._max_retries + 1}), retrying in {delay:.1f}s",
                            extra={"path": path, "params": params, "attempt": attempt + 1},
                        )
                        await asyncio.sleep(delay)
                        continue
                    logger.error(
                        "API timeout (final attempt)",
                        extra={"path": path, "params": params, "attempts": attempt + 1},
                    )
                except httpx.HTTPStatusError as e:
                    status_code = e.response.status_code

                    # Retry on server errors (5xx) and rate limits (429)
                    if status_code >= 500 or status_code == 429:
                        last_exception = e
                        if attempt < self._max_retries:
                            delay = self._backoff_factor**attempt
                            logger.warning(
                                f"API server error {status_code} (attempt {attempt + 1}/{self._max_retries + 1}), retrying in {delay:.1f}s",
                                extra={"path": path, "status": status_code, "attempt": attempt + 1},
                            )
                            await asyncio.sleep(delay)
                            continue

                    # Handle validation errors (422) - try to fix automatically
                    elif status_code == 422:
                        try:
                            error_data = e.response.json()
                            logger.warning(
                                f"API validation error 422: {error_data}",
                                extra={"path": path, "error": error_data},
                            )

                            # Check if it's a limit validation error
                            if isinstance(error_data, list) and len(error_data) > 0:
                                error_info = error_data[0]
                                if error_info.get("type") == "less_than_equal" and error_info.get(
                                    "loc"
                                ) == ["query", "limit"]:
                                    max_allowed = error_info.get("ctx", {}).get("le", 500)
                                    logger.info(
                                        f"API limit validation error, adjusting limit to {max_allowed}"
                                    )
                                    # Modify params to use allowed limit
                                    if params and "limit" in params:
                                        original_limit = params["limit"]
                                        params["limit"] = min(original_limit, max_allowed)
                                        logger.info(
                                            f"Adjusted limit from {original_limit} to {params['limit']}"
                                        )

                                        # Retry with adjusted limit
                                        if attempt < self._max_retries:
                                            delay = 0.5  # Short delay for retry
                                            logger.info(f"Retrying with adjusted limit in {delay}s")
                                            await asyncio.sleep(delay)
                                            continue

                        except Exception as parse_error:
                            logger.warning(f"Could not parse 422 error response: {parse_error}")

                        # If we can't fix it, treat as client error
                        logger.error(f"API validation error 422 (unfixable)", extra={"path": path})
                        raise

                    # Don't retry on other client errors (4xx except 429 and 422)
                    logger.error(
                        f"API client error {status_code}",
                        extra={"path": path, "status": status_code},
                    )
                    raise
                except Exception as e:
                    last_exception = e
                    if attempt < self._max_retries:
                        delay = self._backoff_factor**attempt
                        logger.warning(
                            f"API error (attempt {attempt + 1}/{self._max_retries + 1}), retrying in {delay:.1f}s: {e}",
                            extra={"path": path, "attempt": attempt + 1},
                        )
                        await asyncio.sleep(delay)
                        continue
                    logger.error(
                        f"API error (final attempt): {e}",
                        extra={"path": path, "attempts": attempt + 1},
                    )

            # If we get here, all retries failed
            if last_exception:
                raise last_exception
            raise Exception("API request failed after all retries")

        return await api_circuit_breaker.call(_make_request)

    @ttl_cache(ttl_seconds=120)
    async def get_yield_by_symbol(self, symbol: str, limit: Optional[int] = None) -> Dict[str, Any]:
        params = {"limit": limit} if limit is not None else None
        return await self._get(f"/api/v1/yield/{symbol}", params=params)

    async def get_multiple_yields(
        self, symbols: List[str], limit: Optional[int] = None
    ) -> Dict[str, Any]:
        params = {"symbols": ",".join(symbols), "batch": "true"}
        if limit is not None:
            params["limit"] = limit
        return await self._get("/api/v1/yield/batch", params=params)

    async def get_top(self, limit: int = 20) -> Dict[str, Any]:
        return await self._get("/api/v1/top", params={"limit": limit})

    async def get_top_products(self, limit: int = 10) -> Dict[str, Any]:
        return await self._get("/api/v1/top-products", params={"limit": limit})

    @ttl_cache(ttl_seconds=600)
    async def get_exchanges(
        self, exchange: str, symbol: Optional[str] = None, limit: Optional[int] = None
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = {"exchange": exchange}
        if symbol:
            params["symbol"] = symbol
        if limit is not None:
            params["limit"] = limit
        return await self._get("/api/v1/exchanges", params=params)

    async def get_exchanges_popular(
        self, exchange: str, limit: Optional[int] = None
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = {}
        if limit is not None:
            params["limit"] = limit
        return await self._get(f"/api/v1/exchanges/{exchange}/popular", params=params)

    async def get_htx_products_from_db(self, limit: Optional[int] = None) -> Dict[str, Any]:
        params: Dict[str, Any] = {}
        if limit is not None:
            params["limit"] = limit
        return await self._get("/api/v1/htx/products", params=params)

    async def get_products_popular(
        self, limit: Optional[int] = None, offset: Optional[int] = None
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = {}
        if limit is not None:
            params["limit"] = limit
        if offset is not None:
            params["offset"] = offset
        return await self._get("/api/v1/products/popular", params=params)

    async def get_okx_products(self, limit: Optional[int] = None) -> Dict[str, Any]:
        params = {}
        if limit is not None:
            params["limit"] = limit
        return await self._get("/api/v1/okx/products", params=params)

    async def get_okx_popular(self, limit: Optional[int] = None) -> Dict[str, Any]:
        params = {}
        if limit is not None:
            params["limit"] = limit
        return await self._get("/api/v1/exchanges/okx/popular", params=params)

    async def get_okx_by_symbol(self, symbol: str, limit: Optional[int] = None) -> Dict[str, Any]:
        params: Dict[str, Any] = {"exchange": "okx"}
        if limit is not None:
            params["limit"] = limit
        return await self._get(f"/api/v1/yield/{symbol}", params=params)

    async def get_gate_products(self, limit: Optional[int] = None) -> Dict[str, Any]:
        params = {}
        if limit is not None:
            params["limit"] = limit
        return await self._get("/api/v1/gate/products", params=params)

    async def get_gate_popular(self, limit: Optional[int] = None) -> Dict[str, Any]:
        params = {}
        if limit is not None:
            params["limit"] = limit
        return await self._get("/api/v1/exchanges/gate/popular", params=params)

    async def get_gate_by_symbol(self, symbol: str, limit: Optional[int] = None) -> Dict[str, Any]:
        params: Dict[str, Any] = {"exchange": "gate"}
        if limit is not None:
            params["limit"] = limit
        return await self._get(f"/api/v1/yield/{symbol}", params=params)

    async def get_kucoin_products(self, limit: Optional[int] = None) -> Dict[str, Any]:
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
        lock_period_days: Optional[int] = None,
    ) -> Dict[str, Any]:
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
        return await self._get("/api/v1/stats")

    async def get_kraken_products(
        self, limit: Optional[int] = 50, symbol: Optional[str] = None
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = {}
        if limit is not None:
            params["limit"] = limit
        if symbol:
            params["symbol"] = symbol

        return await self._get("/api/v1/exchanges", params={"exchange": "kraken", **params})

    @ttl_cache(ttl_seconds=900)
    async def get_trending_coins(self) -> Dict[str, Any]:
        return await self._get("/api/v1/coingecko/trending")

    @ttl_cache(ttl_seconds=900)
    async def get_trending_stats(self) -> Dict[str, Any]:
        return await self._get("/api/v1/coingecko/trending-stats")

    @ttl_cache(ttl_seconds=60)
    async def get_priority_products(self, exchange: str) -> Dict[str, Any]:
        return await self._get(f"/api/v1/priority-products/{exchange}")

    async def health(self) -> Dict[str, Any]:
        return await self._get("/api/v1/health")
