"""
Сервіс агрегації - РОЗДІЛ 3.2: Об'єднання всіх компонентів в єдину систему.

Цей модуль реалізує:
- Сервіс агрегації - об'єднання даних з бірж
- Логіка кешування - коли використовувати кеш, коли API
- Обробка помилок - graceful degradation
- Валідація даних - перевірка якості даних
- Логування операцій - для моніторингу

Мета: Об'єднати всі компоненти (Binance, Bybit, кеш, БД) в єдину систему.
"""

from typing import List, Dict, Optional, Any, Tuple
from datetime import datetime, UTC
from dataclasses import dataclass
from enum import Enum

from app.services.exchanges import exchange_registry
from app.services.cache import cache_manager, get_yield_cache_key, get_exchange_cache_key
from app.db.database import db_manager
from app.db.crud import YieldProductCRUD
from app.models.yield_product import YieldProduct
from app.config import settings
from app.utils.logger import logger
from app.utils.metrics import (
    AGGREGATION_REQUESTS,
    AGGREGATION_LATENCY_SECONDS,
    EXTERNAL_API_CALLS,
    CACHE_HITS,
    CACHE_MISSES,
    DB_FALLBACKS,
    observe_latency,
)


class DataSource(Enum):
    """Джерела даних для агрегації."""
    CACHE = "cache"
    DATABASE = "database"
    API_BINANCE = "api_binance"
    API_BYBIT = "api_bybit"
    API_OKX = "api_okx"
    API_MEXC = "api_mexc"
    API_BITMART = "api_bitmart"
    API_GATE = "api_gate"
    API_BITGET = "api_bitget"
    API_KUCOIN = "api_kucoin"
    API_KRAKEN = "api_kraken"
    API_HTX = "api_htx"
    COMBINED = "combined"


class AggregationStrategy(Enum):
    """Стратегії агрегації даних."""
    FAST_CACHE_FIRST = "fast_cache_first"  # Швидкий доступ - кеш першим
    COMPREHENSIVE = "comprehensive"  # Повний - всі джерела
    FALLBACK_CHAIN = "fallback_chain"  # Ланцюжок fallback


@dataclass
class AggregationResult:
    """Результат агрегації даних."""
    data: List[YieldProduct]
    sources_used: List[DataSource]
    cache_hits: int
    cache_misses: int
    api_calls_made: int
    errors_encountered: List[str]
    total_response_time_ms: float
    data_quality_score: float


class DataAggregationService:
    """
    Сервіс агрегації даних з бірж - РОЗДІЛ 3.2.
    
    Об'єднує всі компоненти:
    - Binance та Bybit API
    - Redis кеш
    - PostgreSQL база даних
    - Валідація та обробка помилок
    """
    
    def __init__(self):
        """Ініціалізує сервіс агрегації."""
        self.cache_ttl = settings.cache_expiration
        self.max_retry_attempts = 3
        self.timeout_seconds = 30

        # Популярні символи для перевірки кешу
        self.priority_symbols = ["BTC", "ETH", "USDT", "USDC", "BNB", "SOL", "ADA", "DOT", "MATIC", "AVAX"]
        
        # Налаштування fallback стратегій
        self.fallback_chain = [
            DataSource.CACHE,
            DataSource.DATABASE,
            DataSource.API_BINANCE,
            DataSource.API_BYBIT,
            DataSource.API_OKX,
            DataSource.API_MEXC,
            DataSource.API_BITMART,
            DataSource.API_GATE,
            DataSource.API_BITGET,
            DataSource.API_KRAKEN,
            DataSource.API_HTX
        ]
        
        logger.info("🔄 Сервіс агрегації даних ініціалізовано")
    
    async def aggregate_yield_data(
        self,
        symbol: Optional[str] = None,
        limit: int = 50,
        min_apy: Optional[float] = None,
        provider: Optional[str] = None,
        strategy: AggregationStrategy = AggregationStrategy.FAST_CACHE_FIRST
    ) -> AggregationResult:
        """
        Агрегує дані про yield продукти з різних джерел.
        
        Args:
            symbol: Символ криптовалюти для фільтрації
            limit: Максимальна кількість результатів
            min_apy: Мінімальний APY для фільтрації
            provider: Фільтр по провайдеру
            strategy: Стратегія агрегації
            
        Returns:
            AggregationResult: Результат агрегації з метаданими
        """
        start_time = datetime.now(UTC)
        sources_used = []
        errors = []
        cache_hits = 0
        cache_misses = 0
        api_calls = 0
        
        logger.info(f"🔄 Початок агрегації для {symbol or 'всіх'} символів (стратегія: {strategy.value})")
        logger.info(f"🔍 Деталі запиту: symbol={symbol}, limit={limit}, min_apy={min_apy}, provider={provider}")

        # Перевіряємо повноту кешу перед агрегацією
        if strategy == AggregationStrategy.COMPREHENSIVE:
            cache_complete = await self.validate_cache_completeness()
            logger.info(f"📊 Стан кешу: {'повний' if cache_complete else 'неповний'}")

        AGGREGATION_REQUESTS.labels(strategy=strategy.value).inc()
        
        try:
            aggregated_data = []
            # Вимірюємо загальну латентність агрегації
            with observe_latency(AGGREGATION_LATENCY_SECONDS):
                if strategy == AggregationStrategy.FAST_CACHE_FIRST:
                    aggregated_data, sources, hits, misses = await self._fast_cache_first_aggregation(
                        symbol, limit, min_apy, provider
                    )
                    sources_used.extend(sources)
                    cache_hits += hits
                    cache_misses += misses
                elif strategy == AggregationStrategy.COMPREHENSIVE:
                    aggregated_data, sources, hits, misses, calls = await self._comprehensive_aggregation(
                        symbol, limit, min_apy, provider
                    )
                    sources_used.extend(sources)
                    cache_hits += hits
                    cache_misses += misses
                    api_calls += calls
                elif strategy == AggregationStrategy.FALLBACK_CHAIN:
                    aggregated_data, sources, hits, misses, calls, errs = await self._fallback_chain_aggregation(
                        symbol, limit, min_apy, provider
                    )
                    sources_used.extend(sources)
                    cache_hits += hits
                    cache_misses += misses
                    api_calls += calls
                    errors.extend(errs)
            
            # Застосовуємо фінальну валідацію та обробку
            validated_data = await self._validate_and_process_data(aggregated_data, errors)
            
            # Сортуємо продукти за APY (desc) перед обмеженням limit
            validated_data.sort(key=lambda p: p.apy if p.apy is not None else 0, reverse=True)
            
            # Розраховуємо мітки якості
            response_time = (datetime.now(UTC) - start_time).total_seconds() * 1000
            quality_score = self._calculate_data_quality_score(
                validated_data, sources_used, cache_hits, cache_misses, errors
            )
            
            result = AggregationResult(
                data=validated_data[:limit],  # Обмежуємо результати
                sources_used=sources_used,
                cache_hits=cache_hits,
                cache_misses=cache_misses,
                api_calls_made=api_calls,
                errors_encountered=errors,
                total_response_time_ms=response_time,
                data_quality_score=quality_score
            )
            
            logger.info(
                f"✅ Агрегація завершена: {len(result.data)} продуктів з {len(sources_used)} джерел "
                f"(cache hit rate: {cache_hits}/{cache_hits + cache_misses}, "
                f"якість: {quality_score:.2f})"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Критична помилка агрегації: {e}")
            errors.append(f"Критична помилка: {str(e)}")
            
            return AggregationResult(
                data=[],
                sources_used=[],
                cache_hits=0,
                cache_misses=0,
                api_calls_made=0,
                errors_encountered=errors,
                total_response_time_ms=(datetime.now(UTC) - start_time).total_seconds() * 1000,
                data_quality_score=0.0
            )
    
    async def _fast_cache_first_aggregation(
        self,
        symbol: Optional[str],
        limit: int,
        min_apy: Optional[float],
        provider: Optional[str]
    ) -> Tuple[List[YieldProduct], List[DataSource], int, int]:
        """
        Швидка агрегація з пріоритетом кешу.
        
        Логіка кешування: спочатку кеш, потім БД як fallback.
        """
        sources_used = []
        cache_hits = 0
        cache_misses = 0
        aggregated_data = []
        
        # 1. Спроба отримати з кешу з усіх бірж
        exchanges = ["binance", "bybit"]  # Підтримувані біржі
        cache_hit = False

        for exchange in exchanges:
            if provider and provider.lower() != exchange:
                continue  # Якщо вказаний конкретний провайдер, пропускаємо інші

            cache_key = get_exchange_cache_key(exchange, symbol)
            cached_data = await cache_manager.get_cached_data(cache_key)

            if cached_data is not None and cached_data.get("products"):
                logger.info(f"🎯 Дані з кешу для {exchange} {symbol or 'всіх'}: {len(cached_data['products'])} продуктів")
                cache_hits += 1
                CACHE_HITS.labels(source="redis").inc()
                if not cache_hit:
                    sources_used.append(DataSource.CACHE)
                    cache_hit = True

                # Конвертуємо кешовані дані в YieldProduct
                for item in cached_data["products"]:
                    try:
                        product = YieldProduct(**item)
                        if self._matches_filters(product, symbol, min_apy, provider):
                            aggregated_data.append(product)
                    except Exception as e:
                        logger.warning(f"⚠️ Помилка конвертації кешованого продукту з {exchange}: {e}")

        if not cache_hit:
            cache_misses += len(exchanges)
            CACHE_MISSES.labels(source="redis").inc()

            # 2. Fallback до БД
            logger.info(f"💾 Fallback до БД для {symbol or 'всіх'}")
            try:
                # Використовуємо сесію з db_manager напряму замість get_database_session
                if not hasattr(db_manager, 'session_factory') or not db_manager.session_factory:
                    logger.warning("Database session factory not available, skipping DB fallback")
                    raise Exception("Database not initialized")

                db = db_manager.session_factory()
                try:
                    if symbol:
                        db_products = await YieldProductCRUD.get_products_by_symbol(db, symbol.upper())
                    else:
                        db_products = await YieldProductCRUD.get_all_products(limit, 0)

                    sources_used.append(DataSource.DATABASE)

                    for product in db_products:
                        try:
                            yield_product = YieldProduct(
                                id=product.id,
                                symbol=product.symbol,
                                name=product.name,
                                provider=product.provider,
                                apy=product.apy,
                                is_cefi=product.is_cefi,
                                min_amount=product.min_amount,
                                max_amount=product.max_amount,
                                lock_period_days=product.lock_period_days,
                                max_apy=product.max_apy,
                                risk_level=product.risk_level,
                                is_active=product.is_active,
                                website_url=product.website_url,
                                description=product.description,
                                created_at=product.created_at,
                                updated_at=product.updated_at,
                                last_checked=product.last_checked,
                                raw_data=product.raw_data
                            )

                            if self._matches_filters(yield_product, symbol, min_apy, provider):
                                aggregated_data.append(yield_product)
                        except Exception as e:
                            logger.warning(f"⚠️ Помилка конвертації БД продукту: {e}")
                finally:
                    # Завжди закриваємо сесію
                    try:
                        await db.close()
                    except Exception:
                        pass

            except Exception as e:
                logger.error(f"❌ Помилка fallback до БД: {e}")
                DB_FALLBACKS.labels(reason="db_error").inc()

        return aggregated_data, sources_used, cache_hits, cache_misses
    
    async def _comprehensive_aggregation(
        self,
        symbol: Optional[str],
        limit: int,
        min_apy: Optional[float],
        provider: Optional[str]
    ) -> Tuple[List[YieldProduct], List[DataSource], int, int, int]:
        """
        Повна агрегація з усіх доступних джерел.
        
        Логіка кешування: комбінує кеш, БД та live API дані.
        """
        sources_used = []
        cache_hits = 0
        cache_misses = 0
        api_calls = 0
        aggregated_data = []
        
        # 1. Отримуємо з кешу
        cache_data, sources, hits, misses = await self._get_cached_data(symbol, provider)
        aggregated_data.extend(cache_data)
        sources_used.extend(sources)
        cache_hits += hits
        cache_misses += misses
        
        # 2. Завжди отримуємо з БД для гарантії актуальності (COMPREHENSIVE режим)
        logger.info(f"🔍 COMPREHENSIVE: обов'язково перевіряємо БД для {symbol or 'всіх'}")
        db_data, db_sources = await self._get_database_data(symbol, provider, limit)
        logger.info(f"📊 COMPREHENSIVE: отримано {len(db_data)} продуктів з БД: {[p.provider for p in db_data[:5]]}")
        aggregated_data.extend(db_data)
        sources_used.extend(db_sources)

        # 3. Оновлюємо live дані з API (в COMPREHENSIVE режимі завжди отримуємо свіжі дані)
        logger.info(f"🔄 COMPREHENSIVE: отримуємо свіжі дані з API для {symbol or 'всіх'}")
        api_data, api_sources, calls = await self._get_live_api_data(symbol, provider)
        aggregated_data.extend(api_data)
        sources_used.extend(api_sources)
        api_calls += calls
        
        # Усунення дублікатів
        logger.info(f"📊 COMPREHENSIVE: перед дедуплікацією {len(aggregated_data)} продуктів")
        unique_data = self._deduplicate_products(aggregated_data)
        logger.info(f"📊 COMPREHENSIVE: після дедуплікації {len(unique_data)} продуктів")

        return unique_data, sources_used, cache_hits, cache_misses, api_calls
    
    async def _fallback_chain_aggregation(
        self,
        symbol: Optional[str],
        limit: int,
        min_apy: Optional[float],
        provider: Optional[str]
    ) -> Tuple[List[YieldProduct], List[DataSource], int, int, int, List[str]]:
        """
        Агрегація з ланцюжком fallback.
        
        Обробка помилок: graceful degradation через ланцюжок джерел.
        """
        sources_used = []
        cache_hits = 0
        cache_misses = 0
        api_calls = 0
        errors = []
        aggregated_data = []
        
        for source in self.fallback_chain:
            try:
                if source == DataSource.CACHE:
                    data, sources, hits, misses = await self._get_cached_data(symbol, provider)
                    aggregated_data.extend(data)
                    sources_used.extend(sources)
                    cache_hits += hits
                    cache_misses += misses
                    
                elif source == DataSource.DATABASE:
                    data, sources = await self._get_database_data(symbol, provider, limit)
                    # Додаємо тільки нові дані
                    existing_ids = {p.id for p in aggregated_data}
                    new_data = [p for p in data if p.id not in existing_ids]
                    aggregated_data.extend(new_data)
                    sources_used.extend(sources)
                    
                elif source == DataSource.API_BINANCE:
                    data, sources, calls = await self._get_exchange_data("binance", symbol, provider)
                    existing_ids = {p.id for p in aggregated_data}
                    new_data = [p for p in data if p.id not in existing_ids]
                    aggregated_data.extend(new_data)
                    sources_used.extend(sources)
                    api_calls += calls
                    
                elif source == DataSource.API_BYBIT:
                    data, sources, calls = await self._get_exchange_data("bybit", symbol, provider)
                    existing_ids = {p.id for p in aggregated_data}
                    new_data = [p for p in data if p.id not in existing_ids]
                    aggregated_data.extend(new_data)
                    sources_used.extend(sources)
                    api_calls += calls
                    
                elif source == DataSource.API_OKX:
                    data, sources, calls = await self._get_exchange_data("okx", symbol, provider)
                    existing_ids = {p.id for p in aggregated_data}
                    new_data = [p for p in data if p.id not in existing_ids]
                    aggregated_data.extend(new_data)
                    sources_used.extend(sources)
                    api_calls += calls
                    
                elif source == DataSource.API_MEXC:
                    data, sources, calls = await self._get_exchange_data("mexc", symbol, provider)
                    existing_ids = {p.id for p in aggregated_data}
                    new_data = [p for p in data if p.id not in existing_ids]
                    aggregated_data.extend(new_data)
                    sources_used.extend(sources)
                    api_calls += calls

                elif source == DataSource.API_BITMART:
                    data, sources, calls = await self._get_exchange_data("bitmart", symbol, provider)
                    existing_ids = {p.id for p in aggregated_data}
                    new_data = [p for p in data if p.id not in existing_ids]
                    aggregated_data.extend(new_data)
                    sources_used.extend(sources)
                    api_calls += calls

                elif source == DataSource.API_GATE:
                    data, sources, calls = await self._get_exchange_data("gate", symbol, provider)
                    existing_ids = {p.id for p in aggregated_data}
                    new_data = [p for p in data if p.id not in existing_ids]
                    aggregated_data.extend(new_data)
                    sources_used.extend(sources)
                    api_calls += calls
                    
                elif source == DataSource.API_BITGET:
                    data, sources, calls = await self._get_exchange_data("bitget", symbol, provider)
                    existing_ids = {p.id for p in aggregated_data}
                    new_data = [p for p in data if p.id not in existing_ids]
                    aggregated_data.extend(new_data)
                    sources_used.extend(sources)
                    api_calls += calls

                elif source == DataSource.API_KRAKEN:
                    data, sources, calls = await self._get_exchange_data("kraken", symbol, provider)
                    existing_ids = {p.id for p in aggregated_data}
                    new_data = [p for p in data if p.id not in existing_ids]
                    aggregated_data.extend(new_data)
                    sources_used.extend(sources)
                    api_calls += calls
                
                # Якщо отримали достатньо даних, зупиняємося
                if len(aggregated_data) >= limit:
                    break
                    
            except Exception as e:
                error_msg = f"Помилка {source.value}: {str(e)}"
                errors.append(error_msg)
                logger.warning(f"⚠️ {error_msg}")
                continue
        
        return aggregated_data, sources_used, cache_hits, cache_misses, api_calls, errors
    
    async def _get_cached_data(
        self, symbol: Optional[str], provider: Optional[str]
    ) -> Tuple[List[YieldProduct], List[DataSource], int, int]:
        """Отримує дані з кешу."""
        cache_hits = 0
        cache_misses = 0
        cached_products = []
        sources_used = []
        
        try:
            cache_key = get_yield_cache_key(symbol or "all")
            cached_data = await cache_manager.get_cached_data(cache_key)
            
            if cached_data and cached_data.get("data"):
                cache_hits += 1
                sources_used.append(DataSource.CACHE)
                
                for item in cached_data["data"]:
                    try:
                        product = YieldProduct(**item)
                        if not provider or product.provider.lower() == provider.lower():
                            cached_products.append(product)
                    except Exception as e:
                        logger.warning(f"⚠️ Помилка обробки кешованого продукту: {e}")
            else:
                cache_misses += 1
                
        except Exception as e:
            logger.error(f"❌ Помилка доступу до кешу: {e}")
            cache_misses += 1
        
        return cached_products, sources_used, cache_hits, cache_misses
    
    async def _get_database_data(
        self, symbol: Optional[str], provider: Optional[str], limit: Optional[int] = None
    ) -> Tuple[List[YieldProduct], List[DataSource]]:
        """Отримує дані з бази даних."""
        db_products = []
        sources_used = []
        
        try:
            # Використовуємо сесію з db_manager напряму замість get_database_session
            if not hasattr(db_manager, 'session_factory') or not db_manager.session_factory:
                logger.warning("Database session factory not available, skipping DB query")
                raise Exception("Database not initialized")

            db = db_manager.session_factory()
            try:
                if symbol:
                    logger.info(f"🔍 Викликаємо YieldProductCRUD.get_products_by_symbol(db, {symbol.upper()})")
                    products = await YieldProductCRUD.get_products_by_symbol(db, symbol.upper())
                    logger.info(f"📊 YieldProductCRUD повернув {len(products)} продуктів для {symbol}")
                else:
                    if provider:
                        logger.info(f"🔍 Викликаємо YieldProductCRUD.get_products_by_provider(db, {provider})")
                        products = await YieldProductCRUD.get_products_by_provider(db, provider)
                        logger.info(f"📊 YieldProductCRUD повернув {len(products)} продуктів для provider {provider}")
                    else:
                        products = await YieldProductCRUD.get_all_products(limit or 1000, 0)

                sources_used.append(DataSource.DATABASE)
                logger.info(f"📊 _get_database_data: отримано {len(products)} продуктів з БД для {symbol or 'всіх'}")

                for product in products:
                    try:
                        yield_product = YieldProduct(
                            id=product.id,
                            symbol=product.symbol,
                            name=product.name,
                            provider=product.provider,
                            apy=product.apy,
                            is_cefi=product.is_cefi,
                            min_amount=product.min_amount if product.min_amount is not None else 0.0,
                            max_amount=product.max_amount,
                            lock_period_days=product.lock_period_days,
                            max_apy=product.max_apy,
                            risk_level=product.risk_level,
                            is_active=product.is_active,
                            website_url=product.website_url,
                            description=product.description,
                            product_type=product.product_type,
                            created_at=product.created_at,
                            updated_at=product.updated_at,
                            last_checked=product.last_checked,
                            raw_data=product.raw_data
                        )

                        if not provider or yield_product.provider.lower() == provider.lower():
                            db_products.append(yield_product)
                    except Exception as e:
                        logger.warning(f"⚠️ Помилка конвертації БД продукту {product.id if hasattr(product, 'id') else 'unknown'}: {e}")
            finally:
                # Завжди закриваємо сесію
                try:
                    await db.close()
                except Exception:
                    pass

        except Exception as e:
            logger.error(f"❌ Помилка доступу до БД: {e}")

        return db_products, sources_used
    
    async def _get_live_api_data(
        self, symbol: Optional[str], provider: Optional[str]
    ) -> Tuple[List[YieldProduct], List[DataSource], int]:
        """Отримує live дані з API бірж."""
        api_products = []
        sources_used = []
        api_calls = 0
        
        try:
            # Паралелізуємо виклики до бірж для зменшення латентності
            import asyncio

            async def fetch_exchange(exchange_name: str):
                nonlocal api_calls
                if provider and provider.lower() not in [exchange_name, "all"]:
                    return []
                try:
                    logger.info(f"🔄 Агрегація: отримання даних з {exchange_name} для symbol={symbol}")
                    service = exchange_registry.get_exchange_service(exchange_name)
                    data = await service.get_products_with_cache(symbol)
                    logger.info(f"✅ Агрегація: отримано {len(data)} продуктів з {exchange_name}")
                    api_calls += 1
                    if exchange_name == "binance":
                        sources_used.append(DataSource.API_BINANCE)
                        EXTERNAL_API_CALLS.labels(exchange="binance", status="success").inc()
                    elif exchange_name == "bybit":
                        sources_used.append(DataSource.API_BYBIT)
                        EXTERNAL_API_CALLS.labels(exchange="bybit", status="success").inc()
                    elif exchange_name == "okx":
                        sources_used.append(DataSource.API_OKX)
                        EXTERNAL_API_CALLS.labels(exchange="okx", status="success").inc()
                    elif exchange_name == "mexc":
                        sources_used.append(DataSource.API_MEXC)
                        EXTERNAL_API_CALLS.labels(exchange="mexc", status="success").inc()
                        logger.info(f"📊 MEXC: додано в джерела, отримано {len(data)} продуктів")
                    elif exchange_name == "kucoin":
                        sources_used.append(DataSource.API_KUCOIN)
                        EXTERNAL_API_CALLS.labels(exchange="kucoin", status="success").inc()
                    return data
                except Exception as e:
                    logger.error(f"❌ Агрегація: помилка отримання даних {exchange_name}: {e}", exc_info=True)
                    EXTERNAL_API_CALLS.labels(exchange=exchange_name, status="error").inc()
                    return []

            tasks = []
            available_exchanges = exchange_registry.get_available_exchanges()

            for exchange_name in available_exchanges:
                if not provider or provider.lower() in [exchange_name, "all"]:
                    tasks.append(fetch_exchange(exchange_name))

            if tasks:
                results = await asyncio.gather(*tasks, return_exceptions=True)
            else:
                results = []

            # Статистика помилок валідації для групового логування
            validation_errors = []
            total_processed = 0

            for result in results:
                if isinstance(result, Exception):
                    continue
                for item in result:
                    total_processed += 1
                    try:
                        product = YieldProduct(**item)
                        api_products.append(product)
                    except Exception as e:
                        # Збираємо помилки замість індивідуального логування
                        error_msg = str(e)
                        if len(error_msg) > 100:  # Обрізаємо довгі помилки
                            error_msg = error_msg[:97] + "..."
                        validation_errors.append(error_msg)
        except Exception as e:
            logger.error(f"❌ Критична помилка live API: {e}")

        # Груповий лог помилок валідації замість індивідуальних WARNING
        if validation_errors:
            unique_errors = list(set(validation_errors))  # Видаляємо дублікати
            error_counts = {error: validation_errors.count(error) for error in unique_errors}

            logger.warning(f"⚠️ Валідація API продуктів: {len(validation_errors)} помилок з {total_processed} продуктів")
            for error, count in error_counts.items():
                logger.warning(f"  • {error} ({count} випадків)")

        logger.info(f"🎯 Live API: загалом отримано {len(api_products)} продуктів з джерел: {sources_used}")
        return api_products, sources_used, api_calls
    
    async def _get_exchange_data(
        self, exchange: str, symbol: Optional[str], provider: Optional[str]
    ) -> Tuple[List[YieldProduct], List[DataSource], int]:
        """Отримує дані з конкретної біржі."""
        exchange_products = []
        sources_used = []
        api_calls = 0

        try:
            service = exchange_registry.get_exchange_service(exchange)
            await service.initialize()  # Ініціалізація сервісу
            data = await service.get_products_with_cache(symbol)
            api_calls += 1

            if exchange == "binance":
                sources_used.append(DataSource.API_BINANCE)
            elif exchange == "bybit":
                sources_used.append(DataSource.API_BYBIT)
            elif exchange == "okx":
                sources_used.append(DataSource.API_OKX)
            elif exchange == "mexc":
                sources_used.append(DataSource.API_MEXC)
            elif exchange == "gate":
                sources_used.append(DataSource.API_GATE)
            elif exchange == "bitget":
                sources_used.append(DataSource.API_BITGET)
            elif exchange == "kraken":
                sources_used.append(DataSource.API_KRAKEN)
            elif exchange == "htx":
                sources_used.append(DataSource.API_HTX)
            
            for item in data:
                try:
                    product = YieldProduct(**item)
                    if not provider or product.provider.lower() == provider.lower():
                        exchange_products.append(product)
                except Exception as e:
                    logger.warning(f"⚠️ Помилка конвертації {exchange} продукту: {e}")
                    
        except Exception as e:
            logger.error(f"❌ Помилка отримання даних {exchange}: {e}")
        
        return exchange_products, sources_used, api_calls
    
    def _matches_filters(
        self, 
        product: YieldProduct, 
        symbol: Optional[str], 
        min_apy: Optional[float], 
        provider: Optional[str]
    ) -> bool:
        """Перевіряє чи продукт відповідає фільтрам."""
        if symbol and product.symbol.upper() != symbol.upper():
            return False
        
        if min_apy is not None and product.apy < min_apy:
            return False
        
        if provider and product.provider.lower() != provider.lower():
            return False
        
        return True
    
    async def _validate_and_process_data(
        self, 
        products: List[YieldProduct], 
        errors: List[str]
    ) -> List[YieldProduct]:
        """
        Валідація даних - перевірка якості даних.
        """
        validated_products = []
        
        for product in products:
            try:
                # Перевіряємо обов'язкові поля
                if not product.symbol or not product.provider or product.apy is None:
                    logger.warning(f"⚠️ Пропускаємо продукт з неповними даними: {product.id}")
                    continue
                
                # Перевіряємо валідність APY
                if product.apy < 0 or product.apy > 10000:  # Реалістичні межі
                    logger.warning(f"⚠️ Невірний APY {product.apy}% для продукту {product.id}")
                    continue
                
                # Перевіряємо валідність символу
                if not product.symbol.isalnum() or len(product.symbol) < 2:
                    logger.warning(f"⚠️ Невірний символ {product.symbol} для продукту {product.id}")
                    continue
                
                validated_products.append(product)
                
            except Exception as e:
                error_msg = f"Помилка валідації продукту {product.id if hasattr(product, 'id') else 'unknown'}: {e}"
                errors.append(error_msg)
                logger.error(f"❌ {error_msg}")
        
        logger.info(f"✅ Валідовано {len(validated_products)} з {len(products)} продуктів")
        return validated_products
    
    async def validate_cache_completeness(self) -> bool:
        """Перевіряє що кеш містить дані з усіх провайдерів."""
        try:
            # Отримуємо популярні символи для перевірки
            symbols_to_check = self.priority_symbols[:3]  # Перевіряємо перші 3 популярні

            providers_found = set()
            total_checks = 0

            for symbol in symbols_to_check:
                cache_key = get_yield_cache_key(symbol)
                cached_data = await cache_manager.get_cached_data(cache_key)

                if cached_data and cached_data.get("data"):
                    # Збираємо провайдерів з кешу для цього символу
                    for product in cached_data["data"]:
                        if isinstance(product, dict) and "provider" in product:
                            providers_found.add(product["provider"])
                        elif hasattr(product, 'provider'):
                            providers_found.add(product.provider)

                total_checks += 1

            # Перевіряємо що є дані хоча б з 2 провайдерів
            expected_providers = {"Binance", "Bybit"}
            found_providers = providers_found.intersection(expected_providers)

            completeness_score = len(found_providers) / len(expected_providers)

            logger.info(f"📊 Перевірка повноти кешу: знайдено {len(found_providers)}/{len(expected_providers)} провайдерів "
                       f"({completeness_score:.1%}) - {sorted(found_providers)}")

            # Кеш вважається повним якщо є дані хоча б з 1 провайдера
            return len(found_providers) >= 1

        except Exception as e:
            logger.warning(f"⚠️ Помилка перевірки повноти кешу: {e}")
            return False

    def _deduplicate_products(self, products: List[YieldProduct]) -> List[YieldProduct]:
        """Усунення дублікатів на основі ID та провайдера."""
        seen = set()
        unique_products = []

        # Логування розподілу продуктів перед дедуплікацією
        providers = {}
        lock_periods = {}
        for p in products:
            prov = p.provider
            lock = p.lock_period_days
            providers[prov] = providers.get(prov, 0) + 1
            lock_periods[lock] = lock_periods.get(lock, 0) + 1

        logger.info(f"📊 Перед дедуплікацією: {providers} провайдери, lock_periods: {lock_periods}")

        for product in products:
            # Ключ повинен включати провайдера щоб уникнути видалення продуктів з різних бірж
            key = f"{product.provider}_{product.id}" if product.id else f"{product.provider}_{product.symbol}_{product.name}"

            if key not in seen:
                seen.add(key)
                unique_products.append(product)
            else:
                logger.debug(f"🔄 Дублікат видалено: {key}")

        # Логування розподілу після дедуплікації
        providers_after = {}
        lock_periods_after = {}
        for p in unique_products:
            prov = p.provider
            lock = p.lock_period_days
            providers_after[prov] = providers_after.get(prov, 0) + 1
            lock_periods_after[lock] = lock_periods_after.get(lock, 0) + 1

        logger.info(f"📊 Після дедуплікації: {providers_after} провайдери, lock_periods: {lock_periods_after}")
        logger.info(f"🔄 Усунуто {len(products) - len(unique_products)} дублікатів")
        return unique_products
    
    def _calculate_data_quality_score(
        self,
        products: List[YieldProduct],
        sources_used: List[DataSource],
        cache_hits: int,
        cache_misses: int,
        errors: List[str]
    ) -> float:
        """
        Розраховує оцінку якості даних для моніторингу.
        
        Returns:
            float: Оцінка від 0.0 до 1.0
        """
        score = 0.0
        
        # Базова оцінка за кількість продуктів
        if len(products) > 0:
            score += 0.3
        
        # Оцінка за cache hit rate
        total_cache_requests = cache_hits + cache_misses
        if total_cache_requests > 0:
            hit_rate = cache_hits / total_cache_requests
            score += hit_rate * 0.3
        
        # Оцінка за кількість джерел
        unique_sources = len(set(sources_used))
        score += min(unique_sources / 4.0, 1.0) * 0.2
        
        # Штраф за помилки
        error_penalty = min(len(errors) * 0.05, 0.2)
        score = max(0.0, score - error_penalty)
        
        # Бонус за актуальність даних (якщо є live API дані)
        if DataSource.API_BINANCE in sources_used or DataSource.API_BYBIT in sources_used:
            score += 0.2
        
        return min(1.0, score)
    
    async def get_aggregation_stats(self) -> Dict[str, Any]:
        """
        Логування операцій - для моніторингу.
        
        Returns статистику агрегації для моніторингу.
        """
        try:
            cache_stats = await cache_manager.get_cache_stats()
            
            return {
                "cache_stats": cache_stats,
                "available_sources": [source.value for source in DataSource],
                "fallback_chain": [source.value for source in self.fallback_chain],
                "aggregation_strategies": [strategy.value for strategy in AggregationStrategy],
                "service_status": "healthy",
                "timestamp": datetime.now(UTC).isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Помилка отримання статистики агрегації: {e}")
            return {
                "service_status": "error",
                "error": str(e),
                "timestamp": datetime.now(UTC).isoformat()
            }


# Глобальний екземпляр сервісу агрегації
aggregation_service = DataAggregationService()
