import json
import asyncio
from typing import Optional, Any, Dict
from datetime import datetime, UTC
from contextlib import asynccontextmanager

try:
    import redis.asyncio as redis
    from redis.asyncio import Redis, ConnectionError as RedisConnectionError

    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    Redis = None
    RedisConnectionError = Exception

from bot.config import settings
from bot.utils.logger import logger
from bot.utils.metrics import metrics_collector, CACHE_HITS, CACHE_MISSES, BOT_ERRORS_TOTAL


class CacheMetrics:
    def __init__(self):
        self.hits: int = 0
        self.misses: int = 0
        self.sets: int = 0
        self.deletes: int = 0
        self.errors: int = 0

    def get_stats(self) -> Dict[str, int]:
        return {
            "hits": self.hits,
            "misses": self.misses,
            "sets": self.sets,
            "deletes": self.deletes,
            "errors": self.errors,
            "total_operations": self.hits + self.misses + self.sets + self.deletes,
            "hit_ratio": self.hits / max(1, self.hits + self.misses),
        }


class CacheManager:
    def __init__(self):
        self.redis: Optional[Redis] = None
        self.memory_cache: Dict[str, Dict[str, Any]] = {}
        self.metrics = CacheMetrics()
        self.initialized = False
        self._locks: Dict[str, asyncio.Lock] = {}

    async def initialize(self) -> None:
        if self.initialized:
            return

        try:
            if REDIS_AVAILABLE:
                self.redis = redis.Redis.from_url(
                    settings.REDIS_URL,
                    decode_responses=True,
                    socket_connect_timeout=5,
                    socket_timeout=5,
                    retry_on_timeout=True,
                    max_connections=50,
                    retry_on_error=[ConnectionError],
                    health_check_interval=30,
                    socket_keepalive=True,
                )

                await self.redis.ping()
                logger.info("✅ Redis кеш успішно ініціалізований")
            else:
                logger.warning("⚠️ Redis недоступний, використовується in-memory кеш")

        except (RedisConnectionError, Exception) as e:
            logger.warning(f"⚠️ Помилка ініціалізації Redis: {e}. Використовується in-memory кеш")
            self.redis = None

        self.initialized = True

    async def close(self) -> None:
        if self.redis:
            await self.redis.close()
        self.initialized = False

    async def get(self, key: str, default: Any = None) -> Any:
        if not self.initialized:
            await self.initialize()

        try:
            if self.redis:
                value = await self.redis.get(key)
                if value is not None:
                    self.metrics.hits += 1
                    CACHE_HITS.labels(cache_type="redis").inc()
                    return json.loads(value)
                else:
                    self.metrics.misses += 1
                    CACHE_MISSES.labels(cache_type="redis").inc()
                    return default

            if key in self.memory_cache:
                entry = self.memory_cache[key]
                if entry.get("expires_at", 0) > datetime.now(UTC).timestamp():
                    self.metrics.hits += 1
                    CACHE_HITS.labels(cache_type="memory").inc()
                    return entry["data"]
                else:
                    del self.memory_cache[key]

            self.metrics.misses += 1
            CACHE_MISSES.labels(cache_type="memory").inc()
            return default

        except Exception as e:
            self.metrics.errors += 1
            BOT_ERRORS_TOTAL.labels(error_type=type(e).__name__).inc()
            logger.warning(f"Помилка отримання з кешу {key}: {e}")
            return default

    async def set(self, key: str, value: Any, ttl: int = 300) -> bool:
        if not self.initialized:
            await self.initialize()

        try:
            json_value = json.dumps(value, ensure_ascii=False)

            if self.redis:
                try:
                    success = await self.redis.setex(key, ttl, json_value)
                    if success:
                        self.metrics.sets += 1
                        logger.debug(f"✅ Збережено в Redis: {key} (TTL={ttl}s)")
                        return True
                    else:
                        logger.warning(f"⚠️ Redis setex повернув False для {key}")
                except Exception as redis_error:
                    logger.warning(f"⚠️ Помилка Redis при збереженні {key}: {redis_error}")

            expires_at = datetime.now(UTC).timestamp() + ttl
            self.memory_cache[key] = {"data": value, "expires_at": expires_at}
            self.metrics.sets += 1
            logger.debug(f"💾 Збережено в in-memory: {key} (TTL={ttl}s)")
            return True

        except Exception as e:
            self.metrics.errors += 1
            logger.warning(f"Помилка збереження в кеш {key}: {e}", exc_info=True)
            return False

    async def get_stale_revalidate(self, key: str, ttl: int, refresh_func: callable) -> Any:
        if not self.initialized:
            await self.initialize()

        lock_key = f"lock:{key}"
        lock = self._locks.get(lock_key)
        if lock is None:
            lock = asyncio.Lock()
            self._locks[lock_key] = lock

        async with lock:
            try:
                if self.redis:
                    value = await self.redis.get(key)
                    if value is not None:
                        ttl_key = f"{key}:ttl"
                        ttl_value = await self.redis.get(ttl_key)

                        data = json.loads(value)
                        self.metrics.hits += 1

                        if ttl_value and float(ttl_value) > datetime.now(UTC).timestamp():
                            return data

                        logger.info(f"♻️ Дані {key} застарілі, повертаємо стару версію та оновлюємо")
                        asyncio.create_task(self._background_refresh(key, ttl, refresh_func))
                        return data
                    else:
                        self.metrics.misses += 1

                if key in self.memory_cache:
                    entry = self.memory_cache[key]
                    data = entry["data"]
                    expires_at = entry.get("expires_at", 0)
                    current_time = datetime.now(UTC).timestamp()

                    self.metrics.hits += 1

                    if expires_at > current_time:
                        return data

                    logger.info(
                        f"♻️ Дані {key} застарілі (in-memory), повертаємо стару версію та оновлюємо"
                    )
                    asyncio.create_task(self._background_refresh(key, ttl, refresh_func))
                    return data

                self.metrics.misses += 1

            except Exception as e:
                self.metrics.errors += 1
                logger.warning(f"Помилка отримання з кешу {key}: {e}")

            logger.info(f"🔄 Кеш {key} відсутній, чекаємо першої ініціалізації")
            return await self._fetch_and_cache(key, ttl, refresh_func)

    async def clear_all(self) -> bool:
        try:
            if self.redis:
                await self.redis.flushdb()
                logger.info("🧹 Redis кеш очищено")
            self.memory_cache.clear()
            logger.info("🧹 In-memory кеш очищено")
            return True
        except Exception as e:
            logger.warning(f"Помилка очищення кешу: {e}")
            return False

    async def _background_refresh(self, key: str, ttl: int, refresh_func: callable) -> None:
        try:
            logger.debug(f"🔄 Початок фонового оновлення {key}")
            await self._fetch_and_cache(key, ttl, refresh_func)
            logger.debug(f"✅ Фонове оновлення {key} завершено")
        except Exception as e:
            logger.warning(f"⚠️ Помилка фонового оновлення {key}: {e}")

    async def _fetch_and_cache(self, key: str, ttl: int, refresh_func: callable) -> Any:
        try:
            data = await refresh_func()
            if data is not None:
                success = await self.set(key, data, ttl)
                if success:
                    logger.debug(f"💾 Дані {key} успішно оновлені та збережені")
                else:
                    logger.warning(f"⚠️ Не вдалося зберегти дані {key} в кеш")
            return data
        except Exception as e:
            logger.error(f"❌ Помилка отримання даних для {key}: {e}")
            return None

    async def delete(self, key: str) -> bool:
        if not self.initialized:
            await self.initialize()

        try:
            deleted = False

            if self.redis:
                result = await self.redis.delete(key)
                if result > 0:
                    deleted = True

            if key in self.memory_cache:
                del self.memory_cache[key]
                deleted = True

            if deleted:
                self.metrics.deletes += 1

            return deleted

        except Exception as e:
            self.metrics.errors += 1
            logger.warning(f"Помилка видалення з кешу {key}: {e}")
            return False

    async def clear_pattern(self, pattern: str) -> int:
        if not self.initialized:
            await self.initialize()

        try:
            deleted_count = 0

            if self.redis:
                keys = await self.redis.keys(pattern)
                if keys:
                    deleted_count = await self.redis.delete(*keys)

            keys_to_delete = []
            for key in self.memory_cache.keys():
                if self._match_pattern(key, pattern):
                    keys_to_delete.append(key)

            for key in keys_to_delete:
                del self.memory_cache[key]
                deleted_count += 1

            self.metrics.deletes += deleted_count
            return deleted_count

        except Exception as e:
            self.metrics.errors += 1
            logger.warning(f"Помилка очищення кешу за патерном {pattern}: {e}")
            return 0

    def _match_pattern(self, key: str, pattern: str) -> bool:
        if "*" not in pattern:
            return key == pattern

        import fnmatch

        return fnmatch.fnmatch(key, pattern)

    def get_metrics(self) -> Dict[str, Any]:
        return self.metrics.get_stats()


cache_manager = CacheManager()


@asynccontextmanager
async def get_cache_manager():
    await cache_manager.initialize()
    try:
        yield cache_manager
    finally:
        pass


async def measure_cache_operation(operation_name: str, operation_func):
    start_time = datetime.now(UTC)

    try:
        result = await operation_func
        duration = (datetime.now(UTC) - start_time).total_seconds()

        if duration > 0.1:
            logger.info(f"⏱️ Кеш операція '{operation_name}' виконана за {duration:.3f}с")

        return result

    except Exception as e:
        duration = (datetime.now(UTC) - start_time).total_seconds()
        logger.error(f"❌ Помилка кеш операції '{operation_name}' за {duration:.3f}с: {e}")
        raise
