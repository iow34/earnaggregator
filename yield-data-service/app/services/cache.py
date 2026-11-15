import json
import asyncio
from typing import Optional, Dict, Any, Union, List
from datetime import datetime, UTC, timedelta
from contextlib import asynccontextmanager

try:
    import redis.asyncio as redis
    from redis.asyncio import Redis, ConnectionError, TimeoutError as RedisTimeoutError

    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    Redis = None
    ConnectionError = Exception
    RedisTimeoutError = Exception

from app.config import settings, get_redis_url
from app.utils.logger import logger


class CacheStats:
    def __init__(self):
        self.hits: int = 0
        self.misses: int = 0
        self.sets: int = 0
        self.deletes: int = 0
        self.errors: int = 0

    @property
    def total_requests(self) -> int:
        return self.hits + self.misses

    @property
    def hit_rate(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return (self.hits / self.total_requests) * 100.0

    def to_dict(self) -> Dict[str, Union[int, float]]:
        return {
            "hits": self.hits,
            "misses": self.misses,
            "sets": self.sets,
            "deletes": self.deletes,
            "errors": self.errors,
            "total_requests": self.total_requests,
            "hit_rate_percent": round(self.hit_rate, 2),
        }


class CacheManager:
    def __init__(self):
        self.redis_client: Optional[Redis] = None
        self.is_connected: bool = False
        self.stats = CacheStats()
        self._fallback_cache: Dict[str, Dict[str, Any]] = {}
        self._max_fallback_size = 1000

    async def initialize(self) -> bool:
        if not REDIS_AVAILABLE:
            logger.warning("❌ Redis модуль не встановлений")
            return False

        try:
            redis_url = get_redis_url()
            logger.info("Database/cache connection configured")

            self.redis_client = redis.from_url(
                redis_url,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True,
                health_check_interval=30,
            )

            await self.redis_client.ping()
            self.is_connected = True

            logger.info("✅ Redis підключено успішно")
            return True

        except (ConnectionError, RedisTimeoutError, Exception) as e:
            logger.warning(f"⚠️ Redis недоступний: {e}")
            self.is_connected = False
            return False

    async def close(self):
        if self.redis_client:
            await self.redis_client.close()
            self.is_connected = False
            logger.info("🔌 Redis підключення закрито")

    def _get_cache_key(self, key_type: str, identifier: str) -> str:
        return f"{key_type}:{identifier}"

    async def get_cached_data(self, key: str, default: Optional[Any] = None) -> Optional[Any]:
        try:
            if self.is_connected and self.redis_client:
                cached_value = await self.redis_client.get(key)
                if cached_value is not None:
                    self.stats.hits += 1
                    logger.debug(f"🎯 Cache HIT: {key}")
                    return json.loads(cached_value)
                else:
                    self.stats.misses += 1
                    logger.debug(f"❌ Cache MISS: {key}")
                    return default
            else:
                fallback_data = self._fallback_cache.get(key)
                if (
                    fallback_data
                    and fallback_data.get("expires_at", 0) > datetime.now(UTC).timestamp()
                ):
                    self.stats.hits += 1
                    logger.debug(f"🎯 Fallback Cache HIT: {key}")
                    return fallback_data["data"]
                else:
                    self.stats.misses += 1
                    logger.debug(f"❌ Fallback Cache MISS: {key}")

                    if key in self._fallback_cache:
                        del self._fallback_cache[key]
                    return default

        except (json.JSONDecodeError, Exception) as e:
            self.stats.errors += 1
            logger.error(f"❌ Помилка читання кешу {key}: {e}")
            return default

    async def set_cached_data(self, key: str, data: Any, expiration: Optional[int] = None) -> bool:
        try:
            if expiration is None:
                expiration = settings.cache_expiration

            if self.is_connected and self.redis_client:
                json_data = json.dumps(data, default=str, ensure_ascii=False)
                await self.redis_client.setex(key, expiration, json_data)
                self.stats.sets += 1
                logger.debug(f"💾 Cache SET: {key} (TTL: {expiration}s)")
                return True
            else:
                if len(self._fallback_cache) >= self._max_fallback_size:
                    oldest_key = min(
                        self._fallback_cache.keys(),
                        key=lambda k: self._fallback_cache[k].get("created_at", 0),
                    )
                    del self._fallback_cache[oldest_key]

                expires_at = datetime.now(UTC).timestamp() + expiration
                self._fallback_cache[key] = {
                    "data": data,
                    "expires_at": expires_at,
                    "created_at": datetime.now(UTC).timestamp(),
                }
                self.stats.sets += 1
                logger.debug(f"💾 Fallback Cache SET: {key} (TTL: {expiration}s)")
                return True

        except (TypeError, ValueError, Exception) as e:
            self.stats.errors += 1
            logger.error(f"❌ Помилка збереження кешу {key}: {e}")
            return False

    async def delete_cached_data(self, key: str) -> bool:
        try:
            success = False

            if self.is_connected and self.redis_client:
                result = await self.redis_client.delete(key)
                success = result > 0
                if success:
                    logger.debug(f"🗑️ Cache DELETE: {key}")

            if key in self._fallback_cache:
                del self._fallback_cache[key]
                success = True
                logger.debug(f"🗑️ Fallback Cache DELETE: {key}")

            if success:
                self.stats.deletes += 1

            return success

        except Exception as e:
            self.stats.errors += 1
            logger.error(f"❌ Помилка видалення кешу {key}: {e}")
            return False

    async def clear_cache(self, pattern: str = "*") -> int:
        try:
            deleted_count = 0

            if self.is_connected and self.redis_client:
                keys = await self.redis_client.keys(pattern)
                if keys:
                    deleted_count = await self.redis_client.delete(*keys)
                    logger.info(f"🗑️ Очищено {deleted_count} ключів з Redis за патерном: {pattern}")

            fallback_deleted = 0
            keys_to_delete = [
                key for key in self._fallback_cache.keys() if self._match_pattern(key, pattern)
            ]
            for key in keys_to_delete:
                del self._fallback_cache[key]
                fallback_deleted += 1

            if fallback_deleted > 0:
                logger.info(
                    f"🗑️ Очищено {fallback_deleted} ключів з fallback кешу за патерном: {pattern}"
                )

            return deleted_count + fallback_deleted

        except Exception as e:
            self.stats.errors += 1
            logger.error(f"❌ Помилка очищення кешу за патерном {pattern}: {e}")
            return 0

    def _match_pattern(self, key: str, pattern: str) -> bool:
        if pattern == "*":
            return True

        pattern_parts = pattern.replace("*", ".*")
        import re

        return bool(re.match(pattern_parts, key))

    async def get_cache_stats(self) -> Dict[str, Union[int, float]]:
        stats_dict = self.stats.to_dict()

        if self.is_connected and self.redis_client:
            try:
                redis_info = await self.redis_client.info("memory")
                stats_dict.update(
                    {
                        "redis_connected": True,
                        "redis_memory_used": redis_info.get("used_memory_human", "N/A"),
                        "fallback_cache_size": len(self._fallback_cache),
                    }
                )
            except Exception:
                stats_dict["redis_connected"] = False
                stats_dict["fallback_cache_size"] = len(self._fallback_cache)
        else:
            stats_dict.update(
                {"redis_connected": False, "fallback_cache_size": len(self._fallback_cache)}
            )

        return stats_dict

    async def health_check(self) -> Dict[str, Any]:
        try:
            if self.is_connected and self.redis_client:
                start_time = datetime.now(UTC)
                await self.redis_client.ping()
                response_time = (datetime.now(UTC) - start_time).total_seconds()

                return {
                    "status": "healthy",
                    "redis_connected": True,
                    "response_time_ms": round(response_time * 1000, 2),
                    "fallback_active": False,
                }
            else:
                return {
                    "status": "degraded",
                    "redis_connected": False,
                    "fallback_active": True,
                    "fallback_size": len(self._fallback_cache),
                }
        except Exception as e:
            return {
                "status": "unhealthy",
                "redis_connected": False,
                "error": str(e),
                "fallback_active": True,
                "fallback_size": len(self._fallback_cache),
            }


cache_manager = CacheManager()


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================


async def get_cached_data(key: str, default: Optional[Any] = None) -> Optional[Any]:
    return await cache_manager.get_cached_data(key, default)


async def set_cached_data(key: str, data: Any, expiration: Optional[int] = None) -> bool:
    return await cache_manager.set_cached_data(key, data, expiration)


async def delete_cached_data(key: str) -> bool:
    return await cache_manager.delete_cached_data(key)


async def clear_cache(pattern: str = "*") -> int:
    return await cache_manager.clear_cache(pattern)


# =============================================================================
# CACHE KEY STRATEGIES
# =============================================================================


def get_yield_cache_key(symbol: str) -> str:
    return cache_manager._get_cache_key("yield", symbol.upper())


def get_top_cache_key(limit: int = 20) -> str:
    return cache_manager._get_cache_key("top", str(limit))


def get_exchange_cache_key(exchange: str, symbol: str = None) -> str:
    if symbol:
        return cache_manager._get_cache_key("exchange", f"{exchange}:{symbol.upper()}")
    return cache_manager._get_cache_key("exchange", exchange.lower())


def get_recommendations_cache_key(user_id: str) -> str:
    return cache_manager._get_cache_key("recommendations", str(user_id))


# =============================================================================
# CONTEXT MANAGER
# =============================================================================


@asynccontextmanager
async def cache_context():
    try:
        await cache_manager.initialize()
        yield cache_manager
    finally:
        await cache_manager.close()
