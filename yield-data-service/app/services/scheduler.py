"""
Автоматичне оновлення даних - РОЗДІЛ 3.3: Реалізація Scheduler.

Scheduler запускає фонові задачі:
- update_cache_job() - оновлює кеш кожні 12 годин
- update_database_job() - синхронізує БД з API бірж кожні 12 годин
- Оновлює популярні монети (BTC, ETH, USDT, BNB, SOL)
- Оновлює топ-20 за APY

Використовує APScheduler для планування задач.
Обробка помилок: не зупиняє scheduler при помилках.
Моніторинг задач: логування виконання та метрики.
"""

import asyncio
from typing import Optional, Dict, Any, List
from datetime import datetime, UTC
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR

from prometheus_client import Counter, Gauge, Histogram, generate_latest

from app.services.exchanges import exchange_registry
from app.services.cache import cache_manager
from app.services.coingecko_service import coingecko_service
from app.services.priority_products_service import priority_products_service
from app.db.database import get_database_session
from app.utils.logger import logger


class SchedulerMetrics:
    """
    Метрики для моніторингу scheduler - Prometheus compatible.
    """

    def __init__(self):
        # Prometheus метрики
        self.jobs_executed_total = Counter(
            'scheduler_jobs_executed_total',
            'Total number of jobs executed',
            ['job_type']
        )
        self.jobs_failed_total = Counter(
            'scheduler_jobs_failed_total',
            'Total number of jobs failed',
            ['job_type']
        )
        self.cache_updates_total = Counter(
            'scheduler_cache_updates_total',
            'Total number of cache updates'
        )
        self.db_syncs_total = Counter(
            'scheduler_db_syncs_total',
            'Total number of database synchronizations'
        )
        self.api_calls_total = Counter(
            'scheduler_api_calls_total',
            'Total number of API calls made',
            ['exchange']
        )
        self.job_execution_time = Histogram(
            'scheduler_job_execution_time_seconds',
            'Time spent executing jobs',
            ['job_type']
        )
        self.last_execution_time = Gauge(
            'scheduler_last_execution_timestamp',
            'Timestamp of last job execution'
        )

        # Специфічні метрики для бірж
        self.exchange_products_total = Gauge(
            'scheduler_exchange_products_total',
            'Total number of products per exchange',
            ['exchange']
        )
        self.exchange_sync_success_total = Counter(
            'scheduler_exchange_sync_success_total',
            'Total number of successful syncs per exchange',
            ['exchange']
        )
        self.exchange_sync_errors_total = Counter(
            'scheduler_exchange_sync_errors_total',
            'Total number of sync errors per exchange',
            ['exchange']
        )
        self.bitmart_products_count = Gauge(
            'bitmart_products_count',
            'Current number of BitMart products in database'
        )
        self.bitmart_api_calls_total = Counter(
            'bitmart_api_calls_total',
            'Total number of BitMart API calls'
        )
        self.bitmart_sync_duration_seconds = Histogram(
            'bitmart_sync_duration_seconds',
            'Time spent syncing BitMart products'
        )

        # Внутрішні метрики для логіки
        self._jobs_executed: int = 0
        self._jobs_failed: int = 0
        self._cache_updates: int = 0
        self._db_syncs: int = 0
        self._api_calls: int = 0
        self.last_execution: Optional[datetime] = None
        self.last_error: Optional[str] = None
        self.execution_times: List[float] = []

    def generate_prometheus_metrics(self) -> str:
        """Генерує метрики в Prometheus форматі."""
        # Додаткові метрики для cache та інших сервісів
        try:
            from app.services.cache import cache_manager

            # Cache метрики
            cache_stats = cache_manager.get_stats()
            cache_hit_rate = Gauge('cache_hit_rate_percent', 'Cache hit rate percentage')
            cache_memory_used = Gauge('cache_memory_used_bytes', 'Cache memory usage')

            cache_hit_rate.set(cache_stats.get('hit_rate_percent', 0))

            # Конвертуємо memory string to bytes (приблизно)
            memory_str = cache_stats.get('redis_memory_used', '0M')
            if 'M' in memory_str:
                memory_bytes = float(memory_str.replace('M', '')) * 1024 * 1024
            elif 'K' in memory_str:
                memory_bytes = float(memory_str.replace('K', '')) * 1024
            else:
                memory_bytes = 0
            cache_memory_used.set(memory_bytes)

        except Exception as e:
            logger.warning(f"Не вдалося створити cache метрики для Prometheus: {e}")

        # Генеруємо всі метрики
        return generate_latest().decode('utf-8')
        
    def record_execution(self, job_name: str, duration_ms: float, success: bool):
        """Записує метрики виконання задачі."""
        self.last_execution = datetime.now(UTC)
        self.execution_times.append(duration_ms)
        
        # Обмежуємо історію до 100 останніх виконань
        if len(self.execution_times) > 100:
            self.execution_times.pop(0)
        
        # Оновлюємо Prometheus метрики
        duration_seconds = duration_ms / 1000.0

        if success:
            self._jobs_executed += 1
            self.jobs_executed_total.labels(job_type=job_name).inc()
            self.job_execution_time.labels(job_type=job_name).observe(duration_seconds)
            self.last_execution_time.set(datetime.now(UTC).timestamp())
            logger.info(f"📊 Метрика: {job_name} виконано за {duration_ms:.2f}мс")
        else:
            self._jobs_failed += 1
            self.jobs_failed_total.labels(job_type=job_name).inc()
            self.last_error = f"Задача '{job_name}' провалилась"
            logger.error(f"📊 Метрика: {job_name} провалено")
    
    def record_cache_update(self):
        """Записує оновлення кешу."""
        self._cache_updates += 1
        self.cache_updates_total.inc()

    def record_db_sync(self):
        """Записує синхронізацію БД."""
        self._db_syncs += 1
        self.db_syncs_total.inc()

    def record_api_call(self, exchange: str = "unknown"):
        """Записує API виклик."""
        self._api_calls += 1
        self.api_calls_total.labels(exchange=exchange).inc()
    
    def get_average_execution_time(self) -> float:
        """Середній час виконання."""
        if not self.execution_times:
            return 0.0
        return sum(self.execution_times) / len(self.execution_times)
    
    def to_dict(self) -> Dict[str, Any]:
        """Експортує метрики в словник (JSON API)."""
        return {
            "jobs_executed_total": self._jobs_executed,
            "jobs_failed_total": self._jobs_failed,
            "cache_updates_total": self._cache_updates,
            "db_syncs_total": self._db_syncs,
            "api_calls_total": self._api_calls,
            "average_execution_time_ms": round(self.get_average_execution_time(), 2),
            "last_execution": self.last_execution.isoformat() if self.last_execution else None,
            "last_error": self.last_error,
            "uptime_jobs": len(self.execution_times)
        }

class DataScheduler:
    """
    Планувальник автоматичного оновлення даних - РОЗДІЛ 3.3.
    
    Функції:
    - Автоматична синхронізація з API бірж
    - Оновлення кешу
    - Моніторинг та метрики
    - Обробка помилок без зупинки
    """
    
    def __init__(self):
        """Ініціалізує scheduler."""
        self.scheduler: Optional[AsyncIOScheduler] = None
        self.metrics = SchedulerMetrics()
        self.is_running = False
        
        # Популярні монети для пріоритетного оновлення
        self.priority_symbols = ["BTC", "ETH", "USDT", "USDC", "BNB", "SOL", "ADA", "DOT", "MATIC", "AVAX"]
        
        logger.info("🕐 Scheduler ініціалізовано")
    
    async def update_cache_job(self):
        """
        Задача оновлення кешу - кожні 12 годин.
        
        Обновляє:
        - Популярні монети
        - Топ продукти за APY
        - Кеш бірж
        """
        start_time = datetime.now(UTC)
        job_name = "update_cache_job"
        
        try:
            logger.info("🔄 Початок оновлення кешу...")
            
            # Оновлюємо кеш для популярних монет
            for symbol in self.priority_symbols:
                try:
                    # Очищуємо старий кеш для символу
                    await cache_manager.delete_cached_data(f"yield:{symbol}")
                    logger.info(f"🗑️ Очищено кеш для {symbol}")
                    self.metrics.record_cache_update()
                except Exception as e:
                    logger.warning(f"⚠️ Помилка очищення кешу для {symbol}: {e}")
            
            # Очищуємо топ кеш
            try:
                await cache_manager.clear_cache("top:*")
                logger.info("🗑️ Очищено топ кеш")
                self.metrics.record_cache_update()
            except Exception as e:
                logger.warning(f"⚠️ Помилка очищення топ кешу: {e}")
            
            # Очищуємо кеш бірж
            try:
                await cache_manager.clear_cache("exchange:*")
                logger.info("🗑️ Очищено кеш бірж")
                self.metrics.record_cache_update()
            except Exception as e:
                logger.warning(f"⚠️ Помилка очищення кешу бірж: {e}")
            
            duration = (datetime.now(UTC) - start_time).total_seconds() * 1000
            self.metrics.record_execution(job_name, duration, True)
            
            logger.info(f"✅ Оновлення кешу завершено за {duration:.2f}мс")
            
        except Exception as e:
            # Обробка помилок scheduler - не зупиняти при помилках
            duration = (datetime.now(UTC) - start_time).total_seconds() * 1000
            self.metrics.record_execution(job_name, duration, False)
            self.metrics.last_error = str(e)
            
            logger.error(f"❌ Помилка оновлення кешу: {e}")
            # НЕ зупиняємо scheduler - продовжуємо роботу
    
    async def update_database_job(self):
        """
        Задача оновлення БД - збереження нових даних.

        Синхронізує:
        - Binance продукти
        - Bybit продукти
        - Оновлює існуючі дані
        """
        start_time = datetime.now(UTC)
        job_name = "update_database_job"

        try:
            # Переконуємося, що exchange registry ініціалізований
            available_exchanges = exchange_registry.get_available_exchanges()
            if not available_exchanges:
                logger.info("🔄 Ініціалізація exchange registry...")
                await exchange_registry.initialize()
                available_exchanges = exchange_registry.get_available_exchanges()
                logger.info(f"✅ Exchange registry ініціалізовано: {available_exchanges}")

            logger.info("🔄 Початок синхронізації БД з API бірж...")
            
            total_created = 0
            total_updated = 0
            total_errors = 0
            
            # Синхронізуємо Binance
            try:
                logger.info("📥 Синхронізація Binance...")
                if "binance" not in available_exchanges:
                    logger.warning("⚠️ Binance не доступна в registry, пропускаємо")
                    total_errors += 1
                else:
                    binance_service = exchange_registry.get_exchange_service("binance")
                    binance_result = await binance_service.sync_products_to_db()
                    self.metrics.record_db_sync()
                    self.metrics.record_api_call(exchange="binance")
                    
                    if binance_result["status"] == "success":
                        stats = binance_result["sync_stats"]
                        total_created += stats["created"]
                        total_updated += stats["updated"]
                        total_errors += stats["errors"]
                        logger.info(
                            f"✅ Binance: {stats['created']} створено, "
                            f"{stats['updated']} оновлено, {stats['errors']} помилок"
                        )
                    else:
                        logger.warning(f"⚠️ Binance sync warning: {binance_result.get('message')}")
                        
            except Exception as e:
                logger.error(f"❌ Помилка синхронізації Binance: {e}", exc_info=True)
                total_errors += 1
                # Продовжуємо з Bybit навіть якщо Binance провалився
            
            # Синхронізуємо Bybit
            try:
                logger.info("📥 Синхронізація Bybit...")
                if "bybit" not in available_exchanges:
                    logger.warning("⚠️ Bybit не доступна в registry, пропускаємо")
                    total_errors += 1
                else:
                    bybit_service = exchange_registry.get_exchange_service("bybit")
                    bybit_result = await bybit_service.sync_products_to_db()
                    self.metrics.record_db_sync()
                    self.metrics.record_api_call(exchange="bybit")

                    if bybit_result["status"] == "success":
                        stats = bybit_result["sync_stats"]
                        total_created += stats["created"]
                        total_updated += stats["updated"]
                        total_errors += stats["errors"]
                        logger.info(
                            f"✅ Bybit: {stats['created']} створено, "
                            f"{stats['updated']} оновлено, {stats['errors']} помилок"
                        )
                    else:
                        logger.warning(f"⚠️ Bybit sync warning: {bybit_result.get('message')}")

            except Exception as e:
                logger.error(f"❌ Помилка синхронізації Bybit: {e}", exc_info=True)
                total_errors += 1

            # Синхронізуємо Bitget
            try:
                logger.info("📥 Синхронізація Bitget...")
                if "bitget" not in available_exchanges:
                    logger.warning("⚠️ Bitget не доступна в registry, пропускаємо")
                    total_errors += 1
                else:
                    bitget_service = exchange_registry.get_exchange_service("bitget")
                    bitget_result = await bitget_service.sync_products_to_db()
                    self.metrics.record_db_sync()
                    self.metrics.record_api_call(exchange="bitget")

                    if bitget_result["status"] == "success":
                        stats = bitget_result["sync_stats"]
                        total_created += stats["created"]
                        total_updated += stats["updated"]
                        total_errors += stats["errors"]
                        logger.info(
                            f"✅ Bitget: {stats['created']} створено, "
                            f"{stats['updated']} оновлено, {stats['errors']} помилок"
                        )
                    else:
                        logger.warning(f"⚠️ Bitget sync warning: {bitget_result.get('message')}")

            except Exception as e:
                logger.error(f"❌ Помилка синхронізації Bitget: {e}", exc_info=True)
                total_errors += 1

            # Синхронізуємо BitMart
            try:
                logger.info("📥 Синхронізація BitMart...")
                if "bitmart" not in available_exchanges:
                    logger.warning("⚠️ BitMart не доступна в registry, пропускаємо")
                    total_errors += 1
                else:
                    bitmart_start_time = datetime.now(UTC)
                    bitmart_service = exchange_registry.get_exchange_service("bitmart")
                    bitmart_result = await bitmart_service.sync_products_to_db()
                    self.metrics.record_db_sync()
                    self.metrics.record_api_call(exchange="bitmart")
                    self.metrics.bitmart_api_calls_total.inc()

                    bitmart_duration = (datetime.now(UTC) - bitmart_start_time).total_seconds()
                    self.metrics.bitmart_sync_duration_seconds.observe(bitmart_duration)

                    if bitmart_result["status"] == "success":
                        stats = bitmart_result["sync_stats"]
                        total_created += stats["created"]
                        total_updated += stats["updated"]
                        total_errors += stats["errors"]

                        # Оновлюємо метрики BitMart
                        self.metrics.exchange_products_total.labels(exchange="bitmart").set(stats["created"] + stats["updated"])
                        self.metrics.exchange_sync_success_total.labels(exchange="bitmart").inc()
                        self.metrics.bitmart_products_count.set(stats["created"] + stats["updated"])

                        logger.info(
                            f"✅ BitMart: {stats['created']} створено, "
                            f"{stats['updated']} оновлено, {stats['errors']} помилок "
                            f"(час: {bitmart_duration:.2f}с)"
                        )
                    else:
                        self.metrics.exchange_sync_errors_total.labels(exchange="bitmart").inc()
                        logger.warning(f"⚠️ BitMart sync warning: {bitmart_result.get('message')}")

            except Exception as e:
                logger.error(f"❌ Помилка синхронізації BitMart: {e}", exc_info=True)
                total_errors += 1
                self.metrics.exchange_sync_errors_total.labels(exchange="bitmart").inc()
            
            # Синхронізуємо HTX
            try:
                logger.info("📥 Синхронізація HTX...")
                if "htx" not in available_exchanges:
                    logger.warning("⚠️ HTX не доступна в registry, пропускаємо")
                    total_errors += 1
                else:
                    htx_service = exchange_registry.get_exchange_service("htx")
                    htx_result = await htx_service.sync_products_to_db()
                    self.metrics.record_db_sync()
                    self.metrics.record_api_call(exchange="htx")
                    
                    if htx_result["status"] == "success":
                        stats = htx_result["sync_stats"]
                        total_created += stats["created"]
                        total_updated += stats["updated"]
                        total_errors += stats["errors"]
                        logger.info(
                            f"✅ HTX: {stats['created']} створено, "
                            f"{stats['updated']} оновлено, {stats['errors']} помилок"
                        )
                    else:
                        logger.warning(f"⚠️ HTX sync warning: {htx_result.get('message')}")
                        
            except Exception as e:
                logger.error(f"❌ Помилка синхронізації HTX: {e}", exc_info=True)
                total_errors += 1
            
            # Оновлюємо priority_products після синхронізації бірж
            try:
                logger.info("🔄 Оновлення priority_products...")
                async with get_database_session() as db:
                    priority_stats = await priority_products_service.update_all_exchanges(db)
                    logger.info(
                        f"✅ Priority products оновлено: {priority_stats.get('total', 0)} продуктів "
                        f"для {len([k for k in priority_stats.keys() if k != 'total'])} бірж"
                    )
            except Exception as e:
                logger.error(f"❌ Помилка оновлення priority_products: {e}", exc_info=True)
                # Не зупиняємо scheduler при помилці priority_products
            
            # Логування підсумків
            duration = (datetime.now(UTC) - start_time).total_seconds() * 1000
            
            logger.info(
                f"✅ Синхронізація БД завершена: "
                f"{total_created} створено, {total_updated} оновлено, "
                f"{total_errors} помилок, час: {duration:.2f}мс"
            )
            
            # Записуємо метрики
            success = total_errors == 0 or (total_created + total_updated) > 0
            self.metrics.record_execution(job_name, duration, success)
            
        except Exception as e:
            # Обробка помилок scheduler - не зупиняти при помилках
            duration = (datetime.now(UTC) - start_time).total_seconds() * 1000
            self.metrics.record_execution(job_name, duration, False)
            self.metrics.last_error = str(e)
            
            logger.error(f"❌ Критична помилка синхронізації БД: {e}")
            # НЕ зупиняємо scheduler - продовжуємо роботу
    
    async def health_check_job(self):
        """
        Задача перевірки здоров'я API бірж.
        
        Моніторинг:
        - Alerting при падінні API бірж
        - Логування стану підключень
        """
        start_time = datetime.now(UTC)
        job_name = "health_check_job"
        
        try:
            logger.info("🏥 Перевірка здоров'я API бірж...")
            
            # Перевіряємо Binance
            try:
                binance_service = exchange_registry.get_exchange_service("binance")
                binance_health = await binance_service.test_connection()
                if binance_health["status"] == "success":
                    logger.info(f"✅ Binance API: {binance_health['response_time_ms']}ms")
                else:
                    # Alerting при падінні API
                    logger.error(f"🚨 ALERT: Binance API недоступний! {binance_health.get('message')}")
                    self.metrics.last_error = f"Binance API down: {binance_health.get('message')}"
            except Exception as e:
                logger.error(f"🚨 ALERT: Помилка перевірки Binance API: {e}")
            
            # Перевіряємо Bybit
            try:
                bybit_service = exchange_registry.get_exchange_service("bybit")
                bybit_health = await bybit_service.test_connection()
                if bybit_health["status"] == "success":
                    logger.info(f"✅ Bybit API: {bybit_health['response_time_ms']}ms")
                else:
                    # Alerting при падінні API
                    logger.error(f"🚨 ALERT: Bybit API недоступний! {bybit_health.get('message')}")
                    self.metrics.last_error = f"Bybit API down: {bybit_health.get('message')}"
            except Exception as e:
                logger.error(f"🚨 ALERT: Помилка перевірки Bybit API: {e}")
            
            duration = (datetime.now(UTC) - start_time).total_seconds() * 1000
            self.metrics.record_execution(job_name, duration, True)
            
        except Exception as e:
            duration = (datetime.now(UTC) - start_time).total_seconds() * 1000
            self.metrics.record_execution(job_name, duration, False)
            logger.error(f"❌ Помилка health check job: {e}")
    
    async def update_popular_symbols_job(self):
        """
        Оновлення популярних монет для прогріву кешу.
        """
        start_time = datetime.now(UTC)
        job_name = "update_popular_symbols_job"
        
        try:
            logger.info(f"🔥 Прогрів кешу для популярних монет: {self.priority_symbols}")
            
            for symbol in self.priority_symbols:
                try:
                    # Для кожного популярного символу отримуємо свіжі дані
                    binance_service = exchange_registry.get_exchange_service("binance")
                    bybit_service = exchange_registry.get_exchange_service("bybit")
                    binance_products = await binance_service.get_products_with_cache(symbol)
                    bybit_products = await bybit_service.get_products_with_cache(symbol)
                    
                    total_products = len(binance_products) + len(bybit_products)
                    
                    if total_products > 0:
                        logger.info(f"✅ {symbol}: {total_products} продуктів закешовано")
                    
                    # Невелика пауза між запитами
                    await asyncio.sleep(0.5)
                    
                except Exception as e:
                    logger.warning(f"⚠️ Помилка прогріву кешу для {symbol}: {e}")
            
            duration = (datetime.now(UTC) - start_time).total_seconds() * 1000
            self.metrics.record_execution(job_name, duration, True)
            
            logger.info(f"✅ Прогрів кешу завершено за {duration:.2f}мс")
            
        except Exception as e:
            duration = (datetime.now(UTC) - start_time).total_seconds() * 1000
            self.metrics.record_execution(job_name, duration, False)
            logger.error(f"❌ Помилка прогріву кешу: {e}")
    
    async def update_coingecko_job(self):
        """
        Оновлення рейтингу популярності монет з CoinGecko API - раз на добу.
        """
        start_time = datetime.now(UTC)
        job_name = "update_coingecko_job"
        
        try:
            logger.info("🔄 Початок оновлення рейтингу популярності монет з CoinGecko...")
            
            result = await coingecko_service.update_coins_popularity()
            
            if result.get("success"):
                logger.info(
                    f"✅ CoinGecko оновлено: {result.get('coins_updated', 0)} монет "
                    f"за {result.get('duration_seconds', 0):.2f}с"
                )
            else:
                logger.warning(f"⚠️ CoinGecko оновлення не вдалося: {result.get('message')}")
            
            duration = (datetime.now(UTC) - start_time).total_seconds() * 1000
            self.metrics.record_execution(job_name, duration, result.get("success", False))
            
        except Exception as e:
            duration = (datetime.now(UTC) - start_time).total_seconds() * 1000
            self.metrics.record_execution(job_name, duration, False)
            logger.error(f"❌ Помилка оновлення CoinGecko: {e}", exc_info=True)
    
    def _job_listener(self, event):
        """
        Listener для подій scheduler - логування виконання.
        """
        if event.exception:
            logger.error(f"🚨 Scheduler job {event.job_id} провалено: {event.exception}")
        else:
            logger.debug(f"✅ Scheduler job {event.job_id} виконано успішно")
    
    async def start(self):
        """
        Запускає scheduler з усіма задачами.
        
        Задачі:
        - update_cache_job: кожні 12 годин
        - update_database_job: кожні 12 годин
        - health_check_job: кожні 8 годин
        - update_popular_symbols_job: кожні 6 годин
        - update_coingecko_job: раз на добу (о 00:00 UTC)
        """
        try:
            logger.info("🚀 Запуск scheduler...")
            
            # Створюємо scheduler
            self.scheduler = AsyncIOScheduler(timezone="UTC")
            
            # Додаємо listener для моніторингу
            self.scheduler.add_listener(
                self._job_listener,
                EVENT_JOB_EXECUTED | EVENT_JOB_ERROR
            )
            
            # Задача 1: Оновлення кешу кожні 12 годин
            self.scheduler.add_job(
                self.update_cache_job,
                trigger=IntervalTrigger(hours=12),
                id="update_cache",
                name="Оновлення кешу",
                replace_existing=True,
                max_instances=1  # Тільки одна задача одночасно
            )
            logger.info("✅ Додано задачу: Оновлення кешу (кожні 12 годин)")
            
            # Задача 2: Оновлення БД кожні 12 годин
            self.scheduler.add_job(
                self.update_database_job,
                trigger=IntervalTrigger(hours=12),
                id="update_database",
                name="Синхронізація БД",
                replace_existing=True,
                max_instances=1
            )
            logger.info("✅ Додано задачу: Синхронізація БД (кожні 12 годин)")
            
            # Задача 3: Health check кожні 8 годин
            self.scheduler.add_job(
                self.health_check_job,
                trigger=IntervalTrigger(hours=8),
                id="health_check",
                name="Health Check API",
                replace_existing=True,
                max_instances=1
            )
            logger.info("✅ Додано задачу: Health Check (кожні 8 годин)")
            
            # Задача 4: Прогрів популярних символів кожні 6 годин
            self.scheduler.add_job(
                self.update_popular_symbols_job,
                trigger=IntervalTrigger(hours=6),
                id="warmup_cache",
                name="Прогрів кешу популярних монет",
                replace_existing=True,
                max_instances=1
            )
            logger.info("✅ Додано задачу: Прогрів кешу (кожні 6 годин)")
            
            # Задача 5: Оновлення CoinGecko рейтингу раз на добу (о 00:00 UTC)
            self.scheduler.add_job(
                self.update_coingecko_job,
                trigger=CronTrigger(hour=0, minute=0, timezone="UTC"),
                id="update_coingecko",
                name="Оновлення CoinGecko рейтингу",
                replace_existing=True,
                max_instances=1
            )
            logger.info("✅ Додано задачу: Оновлення CoinGecko рейтингу (раз на добу о 00:00 UTC)")
            
            # Запускаємо scheduler
            self.scheduler.start()
            self.is_running = True
            
            logger.info("✅ Scheduler запущено успішно")
            logger.info("📅 Наступні виконання:")
            for job in self.scheduler.get_jobs():
                next_run = job.next_run_time
                logger.info(f"   - {job.name}: {next_run}")
            
            # Виконуємо перше оновлення одразу
            logger.info("🔄 Запуск першого оновлення...")
            await self._run_initial_sync()
            
        except Exception as e:
            logger.error(f"❌ Помилка запуску scheduler: {e}")
            self.is_running = False
            raise
    
    async def _run_initial_sync(self):
        """
        Перше оновлення при старті.
        
        Виконує:
        - Health check API
        - Прогрів кешу для популярних монет
        """
        try:
            logger.info("🔥 Початкове оновлення при старті...")
            
            # Health check
            await self.health_check_job()
            
            # Невелика пауза
            await asyncio.sleep(2)
            
            # Прогрів кешу
            await self.update_popular_symbols_job()
            
            logger.info("✅ Початкове оновлення завершено")
            
        except Exception as e:
            logger.error(f"❌ Помилка початкового оновлення: {e}")
            # Продовжуємо навіть при помилці
    
    def stop(self):
        """
        Зупиняє scheduler.
        """
        if self.scheduler and self.is_running:
            logger.info("🛑 Зупинка scheduler...")
            self.scheduler.shutdown(wait=True)
            self.is_running = False
            logger.info("✅ Scheduler зупинено")
    
    def get_status(self) -> Dict[str, Any]:
        """
        Моніторинг задач - статус scheduler.
        
        Returns:
            Dict з інформацією про стан scheduler
        """
        if not self.scheduler:
            return {
                "status": "not_initialized",
                "running": False,
                "message": "Scheduler не ініціалізовано"
            }
        
        jobs_info = []
        for job in self.scheduler.get_jobs():
            jobs_info.append({
                "id": job.id,
                "name": job.name,
                "next_run": job.next_run_time.isoformat() if job.next_run_time else None,
                "trigger": str(job.trigger)
            })
        
        return {
            "status": "running" if self.is_running else "stopped",
            "running": self.is_running,
            "jobs_count": len(jobs_info),
            "jobs": jobs_info,
            "metrics": self.metrics.to_dict(),
            "priority_symbols": self.priority_symbols
        }
    
    async def get_metrics(self) -> Dict[str, Any]:
        """
        Prometheus metrics для cache hit rate та інших метрик.
        
        Returns:
            Dict з метриками у форматі Prometheus
        """
        # Отримуємо метрики кешу
        cache_stats = await cache_manager.get_cache_stats()
        
        # Комбінуємо з метриками scheduler
        metrics = {
            "scheduler": self.metrics.to_dict(),
            "cache": cache_stats,
            "timestamp": datetime.now(UTC).isoformat()
        }
        
        return metrics


# Глобальний екземпляр scheduler
data_scheduler = DataScheduler()


# =============================================================================
# PUBLIC API
# =============================================================================

def start_scheduler():
    """
    Запускає scheduler (викликається з main.py).
    
    Використання:
        from app.services.scheduler import start_scheduler
        
        # В lifespan або startup event:
        asyncio.create_task(start_scheduler_async())
    """
    logger.info("🕐 Ініціалізація scheduler через start_scheduler()...")
    # Повертаємо scheduler для подальшого використання
    return data_scheduler


async def start_scheduler_async():
    """
    Асинхронний запуск scheduler.
    
    Використання в lifespan:
        @asynccontextmanager
        async def lifespan(app: FastAPI):
            # Startup
            await start_scheduler_async()
            yield
            # Shutdown
            stop_scheduler()
    """
    try:
        await data_scheduler.start()
    except Exception as e:
        logger.error(f"❌ Помилка запуску scheduler: {e}")


def stop_scheduler():
    """Зупиняє scheduler."""
    data_scheduler.stop()


async def get_scheduler_status() -> Dict[str, Any]:
    """Отримує статус scheduler для API endpoint."""
    return data_scheduler.get_status()


async def get_scheduler_metrics() -> Dict[str, Any]:
    """
    Отримує метрики scheduler (Prometheus compatible).
    """
    return await data_scheduler.get_metrics()


# =============================================================================
# MANUAL TRIGGERS (для тестування)
# =============================================================================

async def trigger_cache_update():
    """Ручне оновлення кешу."""
    await data_scheduler.update_cache_job()


async def trigger_db_sync():
    """Ручна синхронізація БД."""
    await data_scheduler.update_database_job()


async def trigger_health_check():
    """Ручна перевірка здоров'я."""
    await data_scheduler.health_check_job()

async def get_prometheus_metrics() -> str:
    """Повертає метрики в Prometheus форматі."""
    return data_scheduler.metrics.generate_prometheus_metrics()
