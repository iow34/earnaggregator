"""
API маршрути (ендпоінти) - РОЗДІЛ 3.1: Створення API endpoints та бізнес-логіки.

Основні ендпоінти (РОЗДІЛ 3.1):
- GET /api/v1/yield/{symbol} - дані по конкретній монеті з валідацією
- GET /api/v1/top?limit=N - топ N пропозицій за APY
- GET /api/v1/exchanges?exchange=X - дані з конкретної біржі
- GET /api/v1/health - статус сервісу

Додаткові ендпоінти:
- GET /api/v1/exchanges/list - список доступних бірж
- GET /api/v1/recommendations/{user_id} - персоналізовані рекомендації
- GET /api/v1/stats - статистика БД
- GET /api/v1/cache/stats - статистика кешу

Всі ендпоінти використовують кеш для економії API кредитів та включають валідацію параметрів.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Path
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List, Optional
from datetime import datetime, UTC

from app.db.database import get_database_session, get_db_transaction
from app.db.crud import YieldProductCRUD, ExchangeDataCRUD, CacheMetadataCRUD, PriorityProductCRUD, get_database_stats
from app.db.models import YieldProductDB, CoinsPopularityDB
from app.models.yield_product import YieldProduct, YieldProductFilter, YieldProductCreate
from app.models.response import (
    YieldResponse, TopByProviderResponse, ErrorResponse, create_success_response,
    create_error_response, HealthResponse, StatsResponse
)
from app.services.cache import cache_manager, get_yield_cache_key, get_top_cache_key
from app.services.exchanges import exchange_registry
from app.services.aggregation_service import aggregation_service, AggregationStrategy, DataSource
from app.services.coingecko_service import coingecko_service
from app.services.scheduler import (
    get_scheduler_status,
    get_scheduler_metrics,
    get_prometheus_metrics,
    trigger_cache_update,
    trigger_db_sync,
    trigger_health_check
)
from app.utils.logger import logger
from app.__version__ import __version__

# Створюємо роутер для основних API
router = APIRouter(prefix="/api/v1", tags=["yield"])

# Окремий роутер для Prometheus метрик (без префіксу)
metrics_router = APIRouter(tags=["metrics"])


@router.get("/yield/batch")
async def get_yield_batch(
    symbols: str = Query(..., description="Список символів через кому (BTC,ETH,USDT)"),
    limit: Optional[int] = Query(default=20, ge=1, le=100, description="Максимальна кількість продуктів на символ"),
    db: AsyncSession = Depends(get_database_session)
):
    """
    Отримати Yield продукти для множини символів (batch запит).
    
    Args:
        symbols: Список символів через кому
        limit: Максимальна кількість продуктів на символ
        db: Сесія бази даних
        
    Returns:
        Dict з продуктами для кожного символу
    """
    try:
        symbol_list = [s.strip().upper() for s in symbols.split(",") if s.strip()]
        
        if not symbol_list:
            return create_error_response(
                error="Не вказано символів",
                details="Параметр symbols повинен містити принаймні один символ"
            )
        
        if len(symbol_list) > 20:
            return create_error_response(
                error="Занадто багато символів",
                details="Максимум 20 символів за один запит"
            )
        
        logger.info(f"🔄 Batch запит yield продуктів для {len(symbol_list)} символів: {symbol_list}")
        
        result_data = {}
        total_count = 0
        
        for symbol in symbol_list:
            try:
                aggregation_result = await aggregation_service.aggregate_yield_data(
                    symbol=symbol,
                    limit=limit or 20,
                    strategy=AggregationStrategy.COMPREHENSIVE
                )
                
                if aggregation_result.data:
                    result_data[symbol] = [p.dict() for p in aggregation_result.data]
                    total_count += len(aggregation_result.data)
                else:
                    result_data[symbol] = []
                    
            except Exception as e:
                logger.warning(f"⚠️ Помилка отримання продуктів для {symbol}: {e}")
                result_data[symbol] = []
        
        return {
            "success": True,
            "data": result_data,
            "count": total_count,
            "symbols_count": len(symbol_list),
            "message": f"Отримано дані для {len(symbol_list)} символів"
        }
        
    except Exception as e:
        logger.error(f"❌ Помилка batch запиту: {e}")
        return create_error_response(
            error="Помилка batch запиту",
            details=str(e)
        )


@router.get("/yield/{symbol}", response_model=YieldResponse)
async def get_yield_by_symbol(
    symbol: str = Path(..., description="Символ криптовалюти (BTC, ETH, USDT)", min_length=2, max_length=10),
    limit: int = Query(default=50, ge=1, le=100, description="Максимальна кількість продуктів"),
    min_apy: Optional[float] = Query(default=None, ge=0, le=1000, description="Мінімальний APY"),
    provider: Optional[str] = Query(default=None, description="Фільтр по провайдеру"),
    db: AsyncSession = Depends(get_database_session)
) -> YieldResponse:
    """
    Отримати Yield продукти для конкретної монети з використанням сервісу агрегації (РОЗДІЛ 3.2).
    
    Args:
        symbol: Символ криптовалюти (наприклад: BTC, ETH) - від 2 до 10 символів
        limit: Максимальна кількість продуктів (1-100)
        min_apy: Мінімальний APY для фільтрації (0-1000)
        provider: Фільтр по провайдеру (binance, bybit, nexo, etc.)
        db: Сесія бази даних
        
    Returns:
        YieldResponse: Список yield продуктів з агрегації з різних джерел
    """
    try:
        # Покращена валідація символу
        symbol_upper = symbol.upper().strip()
        
        # Перевірка на валідні символи (тільки літери та цифри)
        if not symbol_upper.isalnum():
            raise HTTPException(
                status_code=400,
                detail="Символ повинен містити тільки літери та цифри"
            )
        
        logger.info(f"🔄 Запит yield продуктів для {symbol_upper} через сервіс агрегації")
        
        # Використовуємо сервіс агрегації - РОЗДІЛ 3.2
        aggregation_result = await aggregation_service.aggregate_yield_data(
            symbol=symbol_upper,
            limit=limit,
            min_apy=min_apy,
            provider=provider,
            strategy=AggregationStrategy.COMPREHENSIVE  # Повна агрегація з всіх джерел
        )
        
        # Детальне логування джерел та результатів агрегації
        providers_in_result = [p.provider for p in aggregation_result.data[:10]] if aggregation_result.data else []
        sources_used_str = ', '.join([s.value for s in aggregation_result.sources_used])

        logger.info(
            f"📊 Агрегація завершена: {len(aggregation_result.data)} продуктів з джерел [{sources_used_str}]"
        )
        logger.info(
            f"🔍 Провайдери в результаті: {providers_in_result} | "
            f"Час: {aggregation_result.total_response_time_ms:.2f}мс | "
            f"Якість: {aggregation_result.data_quality_score:.2f}"
        )
        
        # Обробка помилок - graceful degradation
        if aggregation_result.errors_encountered:
            logger.warning(f"⚠️ Помилки під час агрегації: {aggregation_result.errors_encountered}")
        
        # Визначаємо джерело даних для відповіді
        primary_source = "aggregated"
        if aggregation_result.sources_used:
            if len(aggregation_result.sources_used) == 1:
                primary_source = aggregation_result.sources_used[0].value
            else:
                primary_source = "combined"
        
        # Визначаємо чи дані з кешу
        from_cache = (
            len(aggregation_result.sources_used) == 1 and 
            aggregation_result.sources_used[0] == DataSource.CACHE
        )
        
        return YieldResponse(
            success=True,
            data=aggregation_result.data,
            count=len(aggregation_result.data),
            cached=from_cache,
            source=primary_source,
            message=f"Знайдено {len(aggregation_result.data)} продуктів для {symbol_upper} (якість: {aggregation_result.data_quality_score:.2f})",
            filters={
                "symbol": symbol_upper,
                "limit": limit,
                "min_apy": min_apy,
                "provider": provider
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Помилка отримання yield продуктів для {symbol}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Внутрішня помилка сервера: {str(e)}"
        )


@router.get("/top", response_model=TopByProviderResponse)
async def get_top_yields(
    limit: int = Query(default=10, ge=1, le=50, description="Кількість продуктів на біржу")
) -> TopByProviderResponse:
    """
    Отримати топ Yield продуктів за APY по кожній біржі окремо.

    Args:
        limit: Кількість продуктів на біржу (1-50)

    Returns:
        TopByProviderResponse: Топ yield продуктів згруповані по provider'ам
    """
    try:
        # Створюємо унікальний ключ для кешу
        cache_key = f"top_by_provider_{limit}"
        logger.info(f"📊 Запит топ {limit} yield продуктів по кожній біржі")

        # Спочатку перевіряємо кеш
        cached_data = await cache_manager.get_cached_data(cache_key)
        if cached_data is not None:
            logger.info(f"🎯 Топ продукти по provider'ам отримано з кешу")
            # Конвертуємо дані з кешу назад в Pydantic моделі
            yield_products_by_provider = {}
            for provider, products_data in cached_data["data"].items():
                yield_products_by_provider[provider] = [YieldProduct(**item) for item in products_data]

            return TopByProviderResponse(
                success=True,
                data=yield_products_by_provider,
                total_count=cached_data["total_count"],
                providers_count=cached_data["providers_count"],
                cached=True,
                source="cache",
                message=f"Знайдено {cached_data['total_count']} топ продуктів по {cached_data['providers_count']} біржам (з кешу)"
            )

        # Якщо в кеші немає - отримуємо з БД
        logger.info(f"💾 Запит топ продуктів по provider'ам до БД")
        async with get_database_session() as db:
            products_by_provider = await YieldProductCRUD.get_top_products_by_provider(db, limit)

            if not products_by_provider:
                logger.warning("⚠️ Топ продукти не знайдено")
                return TopByProviderResponse(
                    success=True,
                    data={},
                    total_count=0,
                    providers_count=0,
                    cached=False,
                    source="database",
                    message="Топ продукти не знайдено"
                )

            # Конвертуємо в Pydantic моделі
            yield_products_by_provider = {}
            total_converted = 0

            for provider, products in products_by_provider.items():
                provider_products = []
                for product in products:
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
                        provider_products.append(yield_product)
                        total_converted += 1
                    except Exception as e:
                        logger.error(f"❌ Помилка конвертації продукту {product.id} від {provider}: {e}")
                        continue

                if provider_products:  # Додаємо тільки якщо є успішно конвертовані продукти
                    yield_products_by_provider[provider] = provider_products

            logger.info(f"✅ Знайдено {total_converted} топ продуктів по {len(yield_products_by_provider)} біржам")

            # Зберігаємо результат в кеш
            cache_data = {
                "data": {
                    provider: [product.model_dump() for product in products]
                    for provider, products in yield_products_by_provider.items()
                },
                "total_count": total_converted,
                "providers_count": len(yield_products_by_provider),
                "timestamp": datetime.now(UTC).isoformat()
            }
            await cache_manager.set_cached_data(cache_key, cache_data)

            return TopByProviderResponse(
                success=True,
                data=yield_products_by_provider,
                total_count=total_converted,
                providers_count=len(yield_products_by_provider),
                cached=False,
                source="database",
                message=f"Топ продукти по {len(yield_products_by_provider)} біржам"
            )
    except Exception as e:
        logger.error(f"❌ Помилка отримання топ продуктів: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Внутрішня помилка сервера: {str(e)}"
        )


@router.get("/products", response_model=YieldResponse)
async def get_all_products(
    limit: int = Query(default=100, ge=1, le=5000, description="Кількість продуктів"),
    offset: int = Query(default=0, ge=0, description="Зміщення"),
    symbol: Optional[str] = Query(default=None, description="Фільтр по символу"),
    provider: Optional[str] = Query(default=None, description="Фільтр по провайдеру"),
    min_apy: Optional[float] = Query(default=None, ge=0, description="Мінімальний APY"),
    max_apy: Optional[float] = Query(default=None, ge=0, description="Максимальний APY"),
    sort_by: Optional[str] = Query(default="popularity", description="Сортування: apy_desc, apy_asc, popularity"),
    lock_period_days: Optional[int] = Query(default=None, description="Фільтр по періоду блокування (0 = Flexible)"),
    db: AsyncSession = Depends(get_database_session)
) -> YieldResponse:
    """
    Отримати всі Yield продукти з фільтрацією.

    Args:
        limit: Кількість продуктів
        offset: Зміщення
        symbol: Фільтр по символу
        provider: Фільтр по провайдеру
        min_apy: Мінімальний APY
        max_apy: Максимальний APY
        sort_by: Сортування (apy_desc, apy_asc, popularity)
        db: Сесія бази даних

    Returns:
        YieldResponse: Список yield продуктів
    """
    try:
        logger.info(f"📋 Запит всіх продуктів з фільтрами: symbol={symbol}, provider={provider}, min_apy={min_apy}, max_apy={max_apy}, lock_period_days={lock_period_days}, sort_by={sort_by}")

        # Створюємо фільтри
        filters = YieldProductFilter(
            symbol=symbol,
            provider=provider,
            min_apy=min_apy,
            max_apy=max_apy,
            lock_period_days=lock_period_days
        )
        logger.info(f"📋 Створено фільтри: {filters.dict(exclude_none=True)}")
        
        # Отримуємо продукти з фільтрацією та сортуванням
        if sort_by == "popularity":
            # ТЕСТ: Прямий SQL запит для діагностики
            logger.info(f"📋 ТЕСТ: Використовуємо прямий SQL запит для сортування за популярністю")
            try:
                # Використовуємо той самий запит що працює в PostgreSQL напряму
                query = (
                    select(YieldProductDB)
                    .outerjoin(
                        CoinsPopularityDB,
                        func.upper(YieldProductDB.symbol) == func.upper(CoinsPopularityDB.symbol)
                    )
                    .where(YieldProductDB.is_active == True)
                    .order_by(
                        func.coalesce(CoinsPopularityDB.market_cap_rank, 9999).asc(),
                        YieldProductDB.apy.desc()
                    )
                )

                # Обмежуємо результат для тестування
                test_limit = min(limit or 100, 20)  # Макс 20 для тестування
                query = query.limit(test_limit)
                if offset > 0:
                    query = query.offset(offset)

                logger.info(f"🔍 Виконуємо SQL запит з limit={test_limit}")
                result = await db.execute(query)
                products = result.scalars().all()

                logger.info(f"📊 SQL запит повернув {len(products)} продуктів")
                if products:
                    symbols = [p.symbol for p in products[:5]]
                    logger.info(f"📊 Перші 5 символів: {symbols}")

                    # Перевіряємо чи BTC є в результатах
                    btc_found = any(p.symbol.upper() == 'BTC' for p in products[:10])
                    logger.info(f"📊 BTC знайдено в перших 10: {btc_found}")

                # Видаляємо дублікати
                seen = set()
                unique_products = []
                for product in products:
                    if product.id not in seen:
                        seen.add(product.id)
                        unique_products.append(product)

                products = unique_products
                logger.info(f"📊 Після видалення дублікатів: {len(products)} продуктів")

            except Exception as e:
                logger.error(f"❌ Помилка в тестовому SQL запиті: {e}", exc_info=True)
                products = await YieldProductCRUD.get_all_products(limit, offset)
        elif any([symbol, provider, min_apy, max_apy, lock_period_days is not None]):
            logger.info(f"📋 Фільтрація продуктів через filter_products: symbol={symbol}, provider={provider}, min_apy={min_apy}, max_apy={max_apy}, lock_period_days={lock_period_days}")
            products = await YieldProductCRUD.filter_products(filters)
            logger.info(f"📋 filter_products повернув {len(products) if products else 0} продуктів")
        else:
            logger.info(f"📋 Отримання всіх продуктів через get_all_products: limit={limit}, offset={offset}")
            products = await YieldProductCRUD.get_all_products(limit, offset)
            logger.info(f"📋 get_all_products повернув {len(products) if products else 0} продуктів")
        
        logger.info(f"📋 Знайдено {len(products) if products else 0} продуктів в БД")
        
        # Сортування продуктів (тільки якщо не сортували за популярністю через JOIN)
        if sort_by and sort_by != "popularity" and products:
            if sort_by == "apy_desc":
                products.sort(key=lambda x: x.apy, reverse=True)
                logger.info("📋 Продукти відсортовані за APY (від більшого)")
            elif sort_by == "apy_asc":
                products.sort(key=lambda x: x.apy)
                logger.info("📋 Продукти відсортовані за APY (від меншого)")

        if not products:
            logger.warning(f"⚠️ Продукти не знайдено в БД. Фільтри: symbol={symbol}, provider={provider}, min_apy={min_apy}, max_apy={max_apy}, lock_period_days={lock_period_days}, sort_by={sort_by}")
            # Перевіряємо чи взагалі є продукти в БД
            try:
                total_count = await db.execute(select(func.count(YieldProductDB.id)).where(YieldProductDB.is_active == True))
                total = total_count.scalar() or 0
                logger.info(f"📊 Загальна кількість активних продуктів в БД: {total}")
            except Exception as e:
                logger.error(f"❌ Помилка підрахунку продуктів: {e}")
            
            return YieldResponse(
                success=True,
                data=[],
                count=0,
                cached=False,
                source="database",
                message="Продукти не знайдено"
            )
        
        # Конвертуємо в Pydantic моделі
        yield_products = []
        for product in products:
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
                yield_products.append(yield_product)
            except Exception as e:
                logger.error(f"❌ Помилка конвертації продукту {product.id}: {e}")
                continue
        
        logger.info(f"✅ Знайдено {len(yield_products)} продуктів")
        return create_success_response(
            data=yield_products,
            message=f"Знайдено {len(yield_products)} продуктів",
            cached=False,
            source="database"
        )
        
    except Exception as e:
        logger.error(f"❌ Помилка отримання продуктів: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Внутрішня помилка сервера: {str(e)}"
        )


@router.get("/stats", response_model=StatsResponse)
async def get_database_statistics():
    """
    Отримати статистику бази даних.
    
    Returns:
        StatsResponse: Статистика БД або базову статистику якщо БД недоступна
    """
    try:
        logger.info("📊 Запит статистики бази даних")
        
        # Перевіряємо доступність БД перед спробою отримання сесії
        from app.db.database import db_manager
        
        if not db_manager.session_factory or not db_manager.engine:
            logger.warning("⚠️ БД недоступна для статистики - не ініціалізована")
            
            # Повертаємо базову статистику кешу
            cache_stats = await cache_manager.get_cache_stats()
            return StatsResponse(
                success=True,
                total_products=0,
                active_products=0,
                providers_count=0,
                symbols_count=0,
                cache_hit_rate=cache_stats.get('hit_rate_percent', 0),
                last_updated=datetime.now(UTC)
            )
        
        # Якщо БД доступна, отримуємо реальну статистику
        from app.db.database import get_db_transaction
        
        async with get_db_transaction() as db:
            stats = await get_database_stats(db)
            
            logger.info("✅ Статистика отримана з БД")
            return StatsResponse(
                success=True,
                total_products=stats.get('total_products', 0),  # Кількість активних продуктів
                active_products=stats.get('total_products', 0),  # Те саме, що і total_products
                providers_count=stats.get('providers_count', 0),
                symbols_count=stats.get('symbols_count', 0),
                cache_hit_rate=stats.get('hit_rate_percent', 0),
                last_updated=datetime.now(UTC)
            )
        
    except Exception as e:
        logger.error(f"❌ Помилка отримання статистики: {e}")
        
        # Fallback до cache статистики
        try:
            cache_stats = await cache_manager.get_cache_stats()
            return StatsResponse(
                success=True,
                total_products=0,
                active_products=0,
                providers_count=0,
                symbols_count=0,
                cache_hit_rate=cache_stats.get('hit_rate_percent', 0),
                last_updated=datetime.now(UTC)
            )
        except Exception as cache_error:
            logger.error(f"❌ Помилка cache статистики: {cache_error}")
            raise HTTPException(
                status_code=500,
                detail=f"Внутрішня помилка сервера: {str(e)}"
            )


@router.post("/products", response_model=YieldResponse)
async def create_yield_product(
    product_data: YieldProductCreate,
    db: AsyncSession = Depends(get_db_transaction)
) -> YieldResponse:
    """
    Створити новий Yield продукт.
    
    Args:
        product_data: Дані для створення продукту
        db: Сесія бази даних в транзакції
        
    Returns:
        YieldResponse: Створений продукт
    """
    try:
        logger.info(f"➕ Створення нового продукту: {product_data.symbol}")
        
        # Створюємо продукт
        created_product = await YieldProductCRUD.create_product(db, product_data)
        
        # Конвертуємо в Pydantic модель
        yield_product = YieldProduct(
            id=created_product.id,
            symbol=created_product.symbol,
            name=created_product.name,
            provider=created_product.provider,
            apy=created_product.apy,
            is_cefi=created_product.is_cefi,
            min_amount=created_product.min_amount,
            max_amount=created_product.max_amount,
            lock_period_days=created_product.lock_period_days,
            max_apy=created_product.max_apy,
            risk_level=created_product.risk_level,
            is_active=created_product.is_active,
            website_url=created_product.website_url,
            description=created_product.description,
            created_at=created_product.created_at,
            updated_at=created_product.updated_at,
            last_checked=created_product.last_checked,
            raw_data=created_product.raw_data
        )
        
        logger.info(f"✅ Продукт {created_product.id} створено")
        return create_success_response(
            data=[yield_product],
            message=f"Продукт {created_product.symbol} створено",
            cached=False,
            source="database"
        )
        
    except Exception as e:
        logger.error(f"❌ Помилка створення продукту: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Внутрішня помилка сервера: {str(e)}"
        )


@router.get("/health", response_model=HealthResponse)
async def health_check_detailed() -> HealthResponse:
    """
    Детальна перевірка здоров'я сервісу.
    
    Returns:
        HealthResponse: Стан сервісу
    """
    try:
        # Перевіряємо БД
        db_status = "unhealthy"
        try:
            # Використовуємо власну сесію для health check
            from app.db.database import db_manager
            if hasattr(db_manager, 'session_factory') and db_manager.session_factory:
                db = db_manager.session_factory()
                try:
                    db_health = await get_database_stats(db)
                    # Перевіряємо чи є дані та чи можна підключитися
                    if db_health and isinstance(db_health.get("total_products"), int):
                        db_status = "healthy"
                        logger.info(f"✅ БД healthy: {db_health.get('total_products')} продуктів")
                    else:
                        db_status = "unhealthy"
                        logger.warning("⚠️ БД не містить даних або недоступна")
                finally:
                    await db.close()
            else:
                db_health = None
                db_status = "unavailable"  # БД не ініціалізована
                logger.info("ℹ️ БД ще не ініціалізована")
        except Exception as e:
            logger.warning(f"⚠️ Помилка перевірки БД: {e}")
            db_status = "unhealthy"
        
        # Перевіряємо Redis кеш
        try:
            cache_health = await cache_manager.health_check()
            cache_status = cache_health.get("status", "unknown")
        except Exception as e:
            logger.warning(f"⚠️ Помилка перевірки кешу: {e}")
            cache_status = "degraded"
        
        # Перевіряємо API бірж
        try:
            binance_service = exchange_registry.get_exchange_service("binance")
            binance_test = await binance_service.test_connection()
            binance_status = binance_test.get("status", "unknown")
        except Exception:
            binance_status = "unknown"

        try:
            bybit_service = exchange_registry.get_exchange_service("bybit")
            bybit_test = await bybit_service.test_connection()
            bybit_status = bybit_test.get("status", "unknown")
        except Exception:
            bybit_status = "unknown"
        
        return HealthResponse(
            success=True,
            service="yield-data-service",
            version=__version__,
            database_status=db_status,
            cache_status=cache_status,
            api_status={
                "binance": binance_status,
                "bybit": bybit_status
            }
        )
        
    except Exception as e:
        logger.error(f"❌ Помилка health check: {e}")
        return HealthResponse(
            success=False,
            service="yield-data-service",
            version=__version__,
            database_status="unhealthy",
            cache_status="unknown",
            api_status={"error": str(e)}
        )


@router.get("/cache/stats")
async def get_cache_stats():
    """Отримати статистику кешу."""
    try:
        stats = await cache_manager.get_cache_stats()
        return {
            "success": True,
            "status": "success",
            "message": "Статистика кешу отримана успішно",
            "data": stats
        }
        
    except Exception as e:
        logger.error(f"❌ Помилка отримання статистики кешу: {e}")
        return create_error_response(
            error="Помилка отримання статистики кешу",
            details=str(e)
        )


@router.post("/cache/clear")
async def clear_cache(pattern: str = "*"):
    """Очистити кеш за патерном."""
    try:
        deleted_count = await cache_manager.clear_cache(pattern)
        return {
            "success": True,
            "status": "success",
            "message": f"Кеш очищено: видалено {deleted_count} ключів",
            "data": {"deleted_count": deleted_count, "pattern": pattern}
        }
        
    except Exception as e:
        logger.error(f"❌ Помилка очищення кешу: {e}")
        return create_error_response(
            error="Помилка очищення кешу",
            details=str(e)
        )


@router.get("/cache/health")
async def get_cache_health():
    """Перевірити стан кешу."""
    try:
        health_info = await cache_manager.health_check()
        return {
            "success": True,
            "status": "success",
            "message": "Стан кешу перевірено",
            "data": health_info
        }
        
    except Exception as e:
        logger.error(f"❌ Помилка перевірки кешу: {e}")
        return create_error_response(
            error="Помилка перевірки кешу",
            details=str(e)
        )


# =============================================================================
# BINANCE API ENDPOINTS
# =============================================================================

@router.get("/binance/test")
async def test_binance_connection():
    """Тестування підключення до Binance API."""
    try:
        binance_service = exchange_registry.get_exchange_service("binance")
        result = await binance_service.test_connection()
        return {
            "success": True,
            "status": "success",
            "message": "Тест підключення до Binance API виконано",
            "data": result
        }
        
    except Exception as e:
        logger.error(f"❌ Помилка тестування Binance API: {e}")
        return create_error_response(
            error="Помилка тестування Binance API",
            details=str(e)
        )


@router.get("/binance/products")
async def get_binance_products(symbol: Optional[str] = Query(None, description="Фільтр по символу")):
    """Отримати продукти Binance з кешуванням."""
    try:
        binance_service = exchange_registry.get_exchange_service("binance")
        products_data = await binance_service.get_products_with_cache(symbol)
        
        # Конвертуємо в YieldProduct моделі
        yield_products = []
        for item in products_data:
            try:
                product = YieldProduct(**item)
                yield_products.append(product)
            except Exception as e:
                logger.warning(f"⚠️ Помилка конвертації продукту Binance: {e}")
        
        return create_success_response(
            data=yield_products,
            message=f"Отримано {len(yield_products)} продуктів Binance",
            cached=True  # Завжди з кешу через сервіс
        )
        
    except Exception as e:
        logger.error(f"❌ Помилка отримання продуктів Binance: {e}")
        return create_error_response(
            error="Помилка отримання продуктів Binance",
            details=str(e)
        )


@router.post("/binance/sync")
async def sync_binance_products(
    symbol: Optional[str] = Query(None, description="Синхронізувати тільки конкретний символ")
):
    """Синхронізувати продукти Binance з API в БД."""
    try:
        binance_service = exchange_registry.get_exchange_service("binance")
        result = await binance_service.sync_products_to_db(symbol)
        
        if result["status"] == "success":
            return {
                "success": True,
                "status": "success",
                "message": f"Синхронізація Binance завершена: {result['sync_stats']['created']} створено, {result['sync_stats']['updated']} оновлено",
                "data": result
            }
        else:
            return create_error_response(
                error=result.get("message", "Помилка синхронізації"),
                details=str(result)
            )
        
    except Exception as e:
        logger.error(f"❌ Помилка синхронізації Binance: {e}")
        return create_error_response(
            error="Помилка синхронізації Binance",
            details=str(e)
        )


@router.get("/binance/health")
async def get_binance_health():
    """Перевірити стан Binance сервісу."""
    try:
        binance_service = exchange_registry.get_exchange_service("binance")
        health_info = await binance_service.get_health_status()
        return {
            "success": True,
            "status": "success",
            "message": "Стан Binance сервісу перевірено",
            "data": health_info
        }
        
    except Exception as e:
        logger.error(f"❌ Помилка перевірки Binance сервісу: {e}")
        return create_error_response(
            error="Помилка перевірки Binance сервісу",
            details=str(e)
        )


# =============================================================================
# BYBIT API ENDPOINTS
# =============================================================================

@router.get("/bybit/test")
async def test_bybit_connection():
    """Тестування підключення до Bybit API."""
    try:
        bybit_service = exchange_registry.get_exchange_service("bybit")
        result = await bybit_service.test_connection()
        return {
            "success": True,
            "status": "success",
            "message": "Тест підключення до Bybit API виконано",
            "data": result
        }
        
    except Exception as e:
        logger.error(f"❌ Помилка тестування Bybit API: {e}")
        return create_error_response(
            error="Помилка тестування Bybit API",
            details=str(e)
        )


@router.get("/bybit/products")
async def get_bybit_products(symbol: Optional[str] = Query(None, description="Фільтр по символу")):
    """Отримати продукти Bybit з кешуванням."""
    try:
        bybit_service = exchange_registry.get_exchange_service("bybit")
        products_data = await bybit_service.get_products_with_cache(symbol)
        
        # Конвертуємо в YieldProduct моделі
        yield_products = []
        for item in products_data:
            try:
                product = YieldProduct(**item)
                yield_products.append(product)
            except Exception as e:
                logger.warning(f"⚠️ Помилка конвертації продукту Bybit: {e}")
        
        return create_success_response(
            data=yield_products,
            message=f"Отримано {len(yield_products)} продуктів Bybit",
            cached=True  # Завжди з кешу через сервіс
        )
        
    except Exception as e:
        logger.error(f"❌ Помилка отримання продуктів Bybit: {e}")
        return create_error_response(
            error="Помилка отримання продуктів Bybit",
            details=str(e)
        )


@router.post("/bybit/test-full")
async def test_bybit_full_products():
    """Тест отримання всіх Bybit продуктів напряму."""
    try:
        bybit_service = exchange_registry.get_exchange_service("bybit")
        # Отримуємо API клієнт через сервіс
        if hasattr(bybit_service, 'api_client') and bybit_service.api_client:
            products = await bybit_service.api_client.get_earn_products()
        else:
            # Fallback - створюємо новий клієнт
            from app.services.exchanges.bybit.api import BybitAPI
            api_client = BybitAPI("", "")
            products = await api_client.get_earn_products()
        return {
            "success": True,
            "message": f"Отримано {len(products)} продуктів",
            "count": len(products),
            "products": products[:5]  # Повертаємо тільки перші 5 для тесту
        }
    except Exception as e:
        logger.error(f"❌ Помилка тестування Bybit: {e}")
        return create_error_response(
            error="Помилка тестування Bybit",
            details=str(e)
        )

@router.post("/bybit/sync")
async def sync_bybit_products(
    symbol: Optional[str] = Query(None, description="Синхронізувати тільки конкретний символ")
):
    """Синхронізувати продукти Bybit з API в БД."""
    try:
        bybit_service = exchange_registry.get_exchange_service("bybit")
        result = await bybit_service.sync_products_to_db(symbol)
        
        if result["status"] == "success":
            return {
                "success": True,
                "status": "success",
                "message": f"Синхронізація Bybit завершена: {result['sync_stats']['created']} створено, {result['sync_stats']['updated']} оновлено",
                "data": result
            }
        else:
            return create_error_response(
                error=result.get("message", "Помилка синхронізації"),
                details=str(result)
            )
        
    except Exception as e:
        logger.error(f"❌ Помилка синхронізації Bybit: {e}")
        return create_error_response(
            error="Помилка синхронізації Bybit",
            details=str(e)
        )


@router.get("/bybit/health")
async def get_bybit_health():
    """Перевірити стан Bybit сервісу."""
    try:
        bybit_service = exchange_registry.get_exchange_service("bybit")
        health_info = await bybit_service.get_health_status()
        return {
            "success": True,
            "status": "success",
            "message": "Стан Bybit сервісу перевірено",
            "data": health_info
        }
        
    except Exception as e:
        logger.error(f"❌ Помилка перевірки Bybit сервісу: {e}")
        return create_error_response(
            error="Помилка перевірки Bybit сервісу",
            details=str(e)
        )


# =============================================================================
# BITMART API ENDPOINTS
# =============================================================================

@router.post("/bitmart/sync")
async def sync_bitmart_products(
    symbol: Optional[str] = Query(None, description="Синхронізувати тільки конкретний символ")
):
    """Синхронізувати продукти BitMart з API в базу даних."""
    try:
        bitmart_service = exchange_registry.get_exchange_service("bitmart")
        result = await bitmart_service.sync_products_to_db(symbol)
        
        if result.get("status") == "success":
            return {
                "success": True,
                "status": "success",
                "message": f"Синхронізація BitMart завершена: {result['sync_stats']['created']} створено, {result['sync_stats']['updated']} оновлено",
                "data": result
            }
        else:
            return create_error_response(
                error=result.get("message", "Помилка синхронізації"),
                details=str(result)
            )
        
    except Exception as e:
        logger.error(f"❌ Помилка синхронізації BitMart: {e}")
        return create_error_response(
            error="Помилка синхронізації BitMart",
            details=str(e)
        )


@router.get("/bitmart/health")
async def get_bitmart_health():
    """Перевірити стан BitMart сервісу."""
    try:
        bitmart_service = exchange_registry.get_exchange_service("bitmart")
        health_info = await bitmart_service.get_health_status()
        return {
            "success": True,
            "status": "success",
            "message": "Стан BitMart сервісу перевірено",
            "data": health_info
        }
        
    except Exception as e:
        logger.error(f"❌ Помилка перевірки BitMart сервісу: {e}")
        return create_error_response(
            error="Помилка перевірки BitMart сервісу",
            details=str(e)
        )


# =============================================================================
# HTX API ENDPOINTS
# =============================================================================

@router.post("/htx/sync")
async def sync_htx_products(
    symbol: Optional[str] = Query(None, description="Синхронізувати тільки конкретний символ")
):
    """Синхронізувати продукти HTX з API в базу даних."""
    try:
        htx_service = exchange_registry.get_exchange_service("htx")
        result = await htx_service.sync_products_to_db(symbol)
        
        if result.get("status") == "success":
            return {
                "success": True,
                "status": "success",
                "message": f"Синхронізація HTX завершена: {result['sync_stats']['created']} створено, {result['sync_stats']['updated']} оновлено",
                "data": result
            }
        else:
            return create_error_response(
                error=result.get("message", "Помилка синхронізації"),
                details=str(result)
            )
        
    except Exception as e:
        logger.error(f"❌ Помилка синхронізації HTX: {e}")
        return create_error_response(
            error="Помилка синхронізації HTX",
            details=str(e)
        )


@router.get("/htx/health")
async def get_htx_health():
    """Перевірити стан HTX сервісу."""
    try:
        htx_service = exchange_registry.get_exchange_service("htx")
        health_info = await htx_service.get_health_status()
        return {
            "success": True,
            "status": "success",
            "message": "Стан HTX сервісу перевірено",
            "data": health_info
        }
        
    except Exception as e:
        logger.error(f"❌ Помилка перевірки HTX сервісу: {e}")
        return create_error_response(
            error="Помилка перевірки HTX сервісу",
            details=str(e)
        )


# =============================================================================
# OKX API ENDPOINTS
# =============================================================================

@router.get("/okx/test")
async def test_okx_connection():
    """Тестування підключення до OKX API."""
    try:
        okx_service = exchange_registry.get_exchange_service("okx")
        result = await okx_service.test_connection()
        return {
            "success": True,
            "status": "success",
            "message": "Тест підключення до OKX API виконано",
            "data": result
        }

    except Exception as e:
        logger.error(f"❌ Помилка тестування OKX API: {e}")
        return create_error_response(
            error="Помилка тестування OKX API",
            details=str(e)
        )


@router.get("/okx/products")
async def get_okx_products(symbol: Optional[str] = Query(None, description="Фільтр по символу")):
    """Отримати продукти OKX з кешуванням."""
    try:
        okx_service = exchange_registry.get_exchange_service("okx")
        products_data = await okx_service.get_products_with_cache(symbol)

        # Конвертуємо в YieldProduct моделі
        yield_products = []
        for item in products_data:
            try:
                product = YieldProduct(**item)
                yield_products.append(product)
            except Exception as e:
                logger.warning(f"⚠️ Помилка конвертації продукту OKX: {e}")

        return create_success_response(
            data=yield_products,
            message=f"Отримано {len(yield_products)} продуктів OKX",
            cached=True  # Завжди з кешу через сервіс
        )

    except Exception as e:
        logger.error(f"❌ Помилка отримання продуктів OKX: {e}")
        return create_error_response(
            error="Помилка отримання продуктів OKX",
            details=str(e)
        )


@router.post("/okx/sync")
async def sync_okx_products(
    symbol: Optional[str] = Query(None, description="Синхронізувати тільки конкретний символ")
):
    """Синхронізувати продукти OKX з API в БД."""
    try:
        okx_service = exchange_registry.get_exchange_service("okx")
        result = await okx_service.sync_products_to_db(symbol)

        if result["status"] == "success":
            return {
                "success": True,
                "status": "success",
                "message": f"Синхронізація OKX завершена: {result['sync_stats']['created']} створено, {result['sync_stats']['updated']} оновлено",
                "data": result
            }
        else:
            return create_error_response(
                error=result.get("message", "Помилка синхронізації"),
                details=str(result)
            )

    except Exception as e:
        logger.error(f"❌ Помилка синхронізації OKX: {e}")
        return create_error_response(
            error="Помилка синхронізації OKX",
            details=str(e)
        )


@router.get("/okx/health")
async def get_okx_health():
    """Перевірити стан OKX сервісу."""
    try:
        okx_service = exchange_registry.get_exchange_service("okx")
        health_info = await okx_service.get_health_status()
        return {
            "success": True,
            "status": "success",
            "message": "Стан OKX сервісу перевірено",
            "data": health_info
        }

    except Exception as e:
        logger.error(f"❌ Помилка перевірки OKX сервісу: {e}")
        return create_error_response(
            error="Помилка перевірки OKX сервісу",
            details=str(e)
        )


# =============================================================================
# KUCOIN API ENDPOINTS
# =============================================================================

@router.get("/kucoin/test")
async def test_kucoin_connection():
    """Тестування підключення до KuCoin API."""
    try:
        kucoin_service = exchange_registry.get_exchange_service("kucoin")
        result = await kucoin_service.test_connection()
        return {
            "success": True,
            "status": "success",
            "message": "Тест підключення до KuCoin API виконано",
            "data": result,
        }
    except Exception as e:
        logger.error(f"❌ Помилка тестування KuCoin API: {e}")
        return create_error_response(
            error="Помилка тестування KuCoin API",
            details=str(e),
        )


@router.get("/kucoin/products")
async def get_kucoin_products(symbol: Optional[str] = Query(None, description="Фільтр по символу")):
    """Отримати продукти KuCoin з кешуванням."""
    try:
        kucoin_service = exchange_registry.get_exchange_service("kucoin")
        products_data = await kucoin_service.get_products_with_cache(symbol)

        yield_products = []
        for item in products_data:
            try:
                product = YieldProduct(**item)
                yield_products.append(product)
            except Exception as e:
                logger.warning(f"⚠️ Помилка конвертації продукту KuCoin: {e}")

        return create_success_response(
            data=yield_products,
            message=f"Отримано {len(yield_products)} продуктів KuCoin",
            cached=True,
        )
    except Exception as e:
        logger.error(f"❌ Помилка отримання продуктів KuCoin: {e}")
        return create_error_response(
            error="Помилка отримання продуктів KuCoin",
            details=str(e),
        )


@router.post("/kucoin/sync")
async def sync_kucoin_products(symbol: Optional[str] = Query(None, description="Синхронізувати тільки конкретний символ")):
    """Синхронізувати продукти KuCoin з API в БД."""
    try:
        kucoin_service = exchange_registry.get_exchange_service("kucoin")
        result = await kucoin_service.sync_products_to_db(symbol)

        if result["status"] == "success":
            return {
                "success": True,
                "status": "success",
                "message": f"Синхронізація KuCoin завершена: {result['sync_stats']['created']} створено, {result['sync_stats']['updated']} оновлено",
                "data": result,
            }
        else:
            return create_error_response(
                error=result.get("message", "Помилка синхронізації"),
                details=str(result),
            )
    except Exception as e:
        logger.error(f"❌ Помилка синхронізації KuCoin: {e}")
        return create_error_response(
            error="Помилка синхронізації KuCoin",
            details=str(e),
        )


# =============================================================================
# EXCHANGES ENDPOINTS - РОЗДІЛ 3.1: дані з конкретної біржі
# =============================================================================

@router.get("/exchanges")
async def get_exchange_data(
    exchange: Optional[str] = Query(None, description="Назва біржі (binance, bybit). Якщо не вказано, повертає список доступних бірж"),
    symbol: Optional[str] = Query(None, description="Символ монети для фільтрації"),
    limit: int = Query(default=500, ge=1, le=1000, description="Кількість продуктів (макс 1000)"),
    db: AsyncSession = Depends(get_database_session)
):
    """
    Отримати дані з конкретної біржі або список доступних бірж.
    
    Якщо параметр `exchange` не вказано, повертає список доступних бірж.
    Якщо `exchange` вказано, повертає дані з конкретної біржі з використанням сервісу агрегації (РОЗДІЛ 3.2).
    
    Args:
        exchange: Назва біржі (binance, bybit, okx, mexc, bitmart, gate, bitget, kraken, kucoin, htx). Опціонально.
        symbol: Опціональний символ для фільтрації
        limit: Кількість продуктів для повернення
        db: Сесія бази даних
        
    Returns:
        Якщо exchange не вказано: dict зі списком доступних бірж
        Якщо exchange вказано: YieldResponse з даними з конкретної біржі
    """
    # Якщо exchange не вказано, повертаємо список доступних бірж
    if exchange is None:
        try:
            # Перевіряємо стан кожної біржі
            exchanges_status = {}
            
            # Binance
            try:
                binance_service = exchange_registry.get_exchange_service("binance")
                binance_health = await binance_service.get_health_status()
                exchanges_status["binance"] = {
                    "name": "Binance",
                    "status": "healthy" if binance_health.get("status") == "healthy" else "degraded",
                    "description": "Криптобіржа Binance - найбільша у світі",
                    "endpoints": [
                        "/api/v1/exchanges?exchange=binance",
                        "/api/v1/binance/products",
                        "/api/v1/binance/test"
                    ]
                }
            except Exception as e:
                exchanges_status["binance"] = {
                    "name": "Binance", 
                    "status": "unhealthy",
                    "error": str(e)
                }
            
            # Bybit
            try:
                bybit_service = exchange_registry.get_exchange_service("bybit")
                bybit_health = await bybit_service.get_health_status()
                exchanges_status["bybit"] = {
                    "name": "Bybit",
                    "status": "healthy" if bybit_health.get("status") == "healthy" else "degraded",
                    "description": "Криптобіржа Bybit - деривативи та спот торгівля",
                    "endpoints": [
                        "/api/v1/exchanges?exchange=bybit",
                        "/api/v1/bybit/products",
                        "/api/v1/bybit/test"
                    ]
                }
            except Exception as e:
                exchanges_status["bybit"] = {
                    "name": "Bybit",
                    "status": "unhealthy",
                    "error": str(e)
                }

            # OKX
            try:
                okx_service = exchange_registry.get_exchange_service("okx")
                okx_health = await okx_service.get_health_status()
                exchanges_status["okx"] = {
                    "name": "OKX",
                    "status": "healthy" if okx_health.get("status") == "healthy" else "degraded",
                    "description": "Криптобіржа OKX - On-chain та Simple Earn продукти",
                    "endpoints": [
                        "/api/v1/exchanges?exchange=okx",
                        "/api/v1/okx/products",
                        "/api/v1/okx/test"
                    ]
                }
            except Exception as e:
                exchanges_status["okx"] = {
                    "name": "OKX",
                    "status": "unhealthy",
                    "error": str(e)
                }

            # KuCoin
            try:
                kucoin_service = exchange_registry.get_exchange_service("kucoin")
                kucoin_health = await kucoin_service.get_health_status()
                exchanges_status["kucoin"] = {
                    "name": "KuCoin",
                    "status": "healthy" if kucoin_health.get("status") == "healthy" else "degraded",
                    "description": "Криптобіржа KuCoin - Flexible та Fixed Savings",
                    "endpoints": [
                        "/api/v1/exchanges?exchange=kucoin",
                        "/api/v1/kucoin/products",
                        "/api/v1/kucoin/test"
                    ]
                }
            except Exception as e:
                exchanges_status["kucoin"] = {
                    "name": "KuCoin",
                    "status": "unhealthy",
                    "error": str(e)
                }

            return {
                "success": True,
                "exchanges": exchanges_status,
                "total_exchanges": len(exchanges_status),
                "message": "Список доступних бірж отримано"
            }
        except Exception as e:
            logger.error(f"❌ Помилка отримання списку бірж: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Внутрішня помилка сервера: {str(e)}"
            )
    try:
        # Валідація назви біржі
        exchange_lower = exchange.lower().strip()
        if exchange_lower not in ["binance", "bybit", "okx", "mexc", "bitmart", "gate", "bitget", "kraken", "kucoin", "htx"]:
            raise HTTPException(
                status_code=400,
                detail=f"Непідтримувана біржа '{exchange}'. Доступні: binance, bybit, okx, mexc, bitmart, gate, bitget, kraken, kucoin, htx"
            )

        # Mapping для правильного регістру provider імен
        provider_mapping = {
            "binance": "Binance",
            "bybit": "Bybit",
            "okx": "OKX",
            "mexc": "MEXC",
            "bitmart": "BitMart",
            "gate": "gate",
            "bitget": "bitget",
            "kraken": "Kraken",
            "kucoin": "KuCoin",
            "htx": "htx"
        }

        provider_name = provider_mapping.get(exchange_lower, exchange_lower)

        logger.info(f"🏦 Запит даних з біржі {exchange_lower} (provider: {provider_name}) через сервіс агрегації")

        # Використовуємо сервіс агрегації з фільтром по провайдеру - РОЗДІЛ 3.2
        aggregation_result = await aggregation_service.aggregate_yield_data(
            symbol=symbol,
            limit=limit,
            provider=provider_name,  # Фільтруємо по конкретній біржі з правильним регістром
            strategy=AggregationStrategy.COMPREHENSIVE  # Повна агрегація для біржі
        )
        
        # Логування операцій для моніторингу
        logger.info(
            f"📊 Агрегація {exchange_lower}: {len(aggregation_result.data)} продуктів, "
            f"джерела: {[s.value for s in aggregation_result.sources_used]}, "
            f"API виклики: {aggregation_result.api_calls_made}, "
            f"час: {aggregation_result.total_response_time_ms:.2f}мс"
        )
        
        # Обробка помилок - graceful degradation
        if aggregation_result.errors_encountered:
            logger.warning(f"⚠️ Помилки під час агрегації {exchange_lower}: {aggregation_result.errors_encountered}")
        
        # Визначаємо чи дані з кешу
        from_cache = any(source == DataSource.CACHE for source in aggregation_result.sources_used)
        
        return YieldResponse(
            success=True,
            data=aggregation_result.data,
            count=len(aggregation_result.data),
            cached=from_cache,
            source=f"{exchange_lower}_aggregated",
            message=f"Знайдено {len(aggregation_result.data)} продуктів з {exchange_lower} (якість: {aggregation_result.data_quality_score:.2f})"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Помилка отримання даних з {exchange}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Внутрішня помилка сервера: {str(e)}"
        )


@router.get("/exchanges/list")
async def get_available_exchanges():
    """
    Отримати список доступних бірж.
    
    Returns:
        dict: Список доступних бірж з їх статусом
    """
    try:
        # Перевіряємо стан кожної біржі
        exchanges_status = {}
        
        # Binance
        try:
            binance_service = exchange_registry.get_exchange_service("binance")
            binance_health = await binance_service.get_health_status()
            exchanges_status["binance"] = {
                "name": "Binance",
                "status": "healthy" if binance_health.get("status") == "healthy" else "degraded",
                "description": "Криптобіржа Binance - найбільша у світі",
                "endpoints": [
                    "/api/v1/exchanges?exchange=binance",
                    "/api/v1/binance/products",
                    "/api/v1/binance/test"
                ]
            }
        except Exception as e:
            exchanges_status["binance"] = {
                "name": "Binance", 
                "status": "unhealthy",
                "error": str(e)
            }
        
        # Bybit
        try:
            bybit_service = exchange_registry.get_exchange_service("bybit")
            bybit_health = await bybit_service.get_health_status()
            exchanges_status["bybit"] = {
                "name": "Bybit",
                "status": "healthy" if bybit_health.get("status") == "healthy" else "degraded",
                "description": "Криптобіржа Bybit - деривативи та спот торгівля",
                "endpoints": [
                    "/api/v1/exchanges?exchange=bybit",
                    "/api/v1/bybit/products",
                    "/api/v1/bybit/test"
                ]
            }
        except Exception as e:
            exchanges_status["bybit"] = {
                "name": "Bybit",
                "status": "unhealthy",
                "error": str(e)
            }

        # OKX
        try:
            okx_service = exchange_registry.get_exchange_service("okx")
            okx_health = await okx_service.get_health_status()
            exchanges_status["okx"] = {
                "name": "OKX",
                "status": "healthy" if okx_health.get("status") == "healthy" else "degraded",
                "description": "Криптобіржа OKX - On-chain та Simple Earn продукти",
                "endpoints": [
                    "/api/v1/exchanges?exchange=okx",
                    "/api/v1/okx/products",
                    "/api/v1/okx/test"
                ]
            }
        except Exception as e:
            exchanges_status["okx"] = {
                "name": "OKX",
                "status": "unhealthy",
                "error": str(e)
            }

        # KuCoin
        try:
            kucoin_service = exchange_registry.get_exchange_service("kucoin")
            kucoin_health = await kucoin_service.get_health_status()
            exchanges_status["kucoin"] = {
                "name": "KuCoin",
                "status": "healthy" if kucoin_health.get("status") == "healthy" else "degraded",
                "description": "Криптобіржа KuCoin - Flexible та Fixed Savings",
                "endpoints": [
                    "/api/v1/exchanges?exchange=kucoin",
                    "/api/v1/kucoin/products",
                    "/api/v1/kucoin/test"
                ]
            }
        except Exception as e:
            exchanges_status["kucoin"] = {
                "name": "KuCoin",
                "status": "unhealthy",
                "error": str(e)
            }

        return {
            "success": True,
            "exchanges": exchanges_status,
            "total_exchanges": len(exchanges_status),
            "message": "Список доступних бірж отримано"
        }
        
    except Exception as e:
        logger.error(f"❌ Помилка отримання списку бірж: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Внутрішня помилка сервера: {str(e)}"
        )


# =============================================================================
# СЕРВІС АГРЕГАЦІЇ - РОЗДІЛ 3.2: Тестування та моніторинг
# =============================================================================

@router.get("/aggregation/stats")
async def get_aggregation_stats():
    """
    Отримати статистику сервісу агрегації.
    
    Логування операцій - для моніторингу.
    
    Returns:
        dict: Статистика агрегації
    """
    try:
        stats = await aggregation_service.get_aggregation_stats()
        return {
            "success": True,
            "status": "success",
            "message": "Статистика сервісу агрегації отримана",
            "data": stats
        }
        
    except Exception as e:
        logger.error(f"❌ Помилка отримання статистики агрегації: {e}")
        return create_error_response(
            error="Помилка отримання статистики агрегації",
            details=str(e)
        )


@router.get("/aggregation/test")
async def test_aggregation(
    symbol: Optional[str] = Query(None, description="Символ для тестування"),
    strategy: str = Query(default="fast_cache_first", description="Стратегія агрегації"),
    limit: int = Query(default=10, ge=1, le=50, description="Ліміт результатів")
):
    """
    Тестовий endpoint для перевірки роботи сервісу агрегації.
    
    Args:
        symbol: Символ для тестування
        strategy: Стратегія агрегації (fast_cache_first, comprehensive, fallback_chain)
        limit: Ліміт результатів
        
    Returns:
        dict: Результат тестування
    """
    try:
        # Валідація стратегії
        try:
            strategy_enum = AggregationStrategy(strategy)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Невірна стратегія '{strategy}'. Доступні: fast_cache_first, comprehensive, fallback_chain"
            )
        
        logger.info(f"🧪 Тестування агрегації: символ={symbol}, стратегія={strategy}")
        
        # Запускаємо агрегацію
        start_time = datetime.now(UTC)
        result = await aggregation_service.aggregate_yield_data(
            symbol=symbol,
            limit=limit,
            strategy=strategy_enum
        )
        end_time = datetime.now(UTC)
        
        # Формуємо детальний звіт для тестування
        test_report = {
            "test_config": {
                "symbol": symbol,
                "strategy": strategy,
                "limit": limit
            },
            "aggregation_result": {
                "products_found": len(result.data),
                "sources_used": [s.value for s in result.sources_used],
                "cache_hits": result.cache_hits,
                "cache_misses": result.cache_misses,
                "api_calls_made": result.api_calls_made,
                "errors_encountered": result.errors_encountered,
                "total_response_time_ms": result.total_response_time_ms,
                "data_quality_score": result.data_quality_score
            },
            "test_duration_ms": (end_time - start_time).total_seconds() * 1000,
            "timestamp": end_time.isoformat()
        }
        
        logger.info(
            f"✅ Тест агрегації завершено: {len(result.data)} продуктів за {test_report['test_duration_ms']:.2f}мс"
        )
        
        return {
            "success": True,
            "status": "success",
            "message": f"Тест агрегації завершено успішно: знайдено {len(result.data)} продуктів",
            "data": test_report
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Помилка тестування агрегації: {e}")
        return create_error_response(
            error="Помилка тестування агрегації",
            details=str(e)
        )


# =============================================================================
# PROMETHEUS METRICS - РОЗДІЛ 3.3: Моніторинг
# =============================================================================

@metrics_router.get("/metrics")
async def prometheus_metrics_endpoint():
    """
    Prometheus метрики для моніторингу.

    Повертає метрики в native Prometheus форматі для scraping.
    Включає scheduler metrics, cache statistics та інші.

    Returns:
        Response: Метрики в Prometheus форматі
    """
    try:
        metrics = await get_prometheus_metrics()
        return Response(content=metrics, media_type="text/plain; charset=utf-8")
    except Exception as e:
        logger.error(f"❌ Помилка генерації Prometheus метрик: {e}")
        return Response(content="# Error generating metrics\n", media_type="text/plain; charset=utf-8")

# =============================================================================
# SCHEDULER - РОЗДІЛ 3.3: Автоматичне оновлення даних
# =============================================================================

@router.get("/scheduler/status")
async def get_scheduler_status_endpoint():
    """
    Отримати статус scheduler.
    
    Моніторинг задач - статус планувальника.
    
    Returns:
        dict: Інформація про scheduler та його задачі
    """
    try:
        status = await get_scheduler_status()
        return {
            "success": True,
            "status": "success",
            "message": "Статус scheduler отримано",
            "data": status
        }
    except Exception as e:
        logger.error(f"❌ Помилка отримання статусу scheduler: {e}")
        return create_error_response(
            error="Помилка отримання статусу scheduler",
            details=str(e)
        )


@router.get("/scheduler/metrics")
async def get_scheduler_metrics_endpoint():
    """
    Prometheus metrics для scheduler.
    
    Metrics включають:
    - Cache hit rate
    - Jobs executed/failed
    - API calls count
    - Average execution time
    
    Returns:
        dict: Метрики у форматі Prometheus
    """
    try:
        metrics = await get_scheduler_metrics()
        return {
            "success": True,
            "status": "success",
            "message": "Метрики scheduler отримано",
            "data": metrics
        }
    except Exception as e:
        logger.error(f"❌ Помилка отримання метрик scheduler: {e}")
        return create_error_response(
            error="Помилка отримання метрик scheduler",
            details=str(e)
        )


@router.post("/scheduler/trigger/cache")
async def trigger_cache_update_endpoint():
    """
    Ручне оновлення кешу.
    
    Запускає задачу оновлення кешу вручну.
    
    Returns:
        dict: Результат оновлення
    """
    try:
        logger.info("🔄 Ручне оновлення кешу запущено...")
        await trigger_cache_update()
        return {
            "success": True,
            "status": "success",
            "message": "Кеш оновлено вручну",
            "timestamp": datetime.now(UTC).isoformat()
        }
    except Exception as e:
        logger.error(f"❌ Помилка ручного оновлення кешу: {e}")
        return create_error_response(
            error="Помилка ручного оновлення кешу",
            details=str(e)
        )


@router.post("/scheduler/trigger/sync")
async def trigger_db_sync_endpoint():
    """
    Ручна синхронізація БД.
    
    Запускає задачу синхронізації БД вручну.
    
    Returns:
        dict: Результат синхронізації
    """
    try:
        logger.info("🔄 Ручна синхронізація БД запущена...")
        await trigger_db_sync()
        return {
            "success": True,
            "status": "success",
            "message": "БД синхронізовано вручну",
            "timestamp": datetime.now(UTC).isoformat()
        }
    except Exception as e:
        logger.error(f"❌ Помилка ручної синхронізації БД: {e}")
        return create_error_response(
            error="Помилка ручної синхронізації БД",
            details=str(e)
        )


@router.post("/scheduler/trigger/healthcheck")
async def trigger_healthcheck_endpoint():
    """
    Ручна перевірка здоров'я API.
    
    Запускає задачу health check вручну.
    
    Returns:
        dict: Результат перевірки
    """
    try:
        logger.info("🏥 Ручна перевірка здоров'я запущена...")
        await trigger_health_check()
        return {
            "success": True,
            "status": "success",
            "message": "Health check виконано вручну",
            "timestamp": datetime.now(UTC).isoformat()
        }
    except Exception as e:
        logger.error(f"❌ Помилка ручної перевірки здоров'я: {e}")
        return create_error_response(
            error="Помилка ручної перевірки здоров'я",
            details=str(e)
        )


# =============================================================================
# COINGECKO POPULARITY ENDPOINTS
# =============================================================================

@router.post("/coingecko/update-popularity")
async def update_coins_popularity():
    """
    Оновлює рейтинг популярності монет з CoinGecko API.

    Викликає CoinGecko API та зберігає дані в таблицю coins_popularity.
    Рекомендується викликати раз на день.

    Returns:
        dict: Результат оновлення
    """
    try:
        logger.info("[API] 📊 Початок оновлення рейтингу популярності монет")

        # Викликаємо сервіс оновлення
        result = await coingecko_service.update_coins_popularity()

        if result["success"]:
            logger.info(f"[API] ✅ Рейтинг популярності оновлено: {result['message']}")
            return {
                "success": True,
                "message": "Рейтинг популярності успішно оновлено",
                "data": result,
                "timestamp": datetime.now(UTC).isoformat()
            }
        else:
            logger.error(f"[API] ❌ Помилка оновлення популярності: {result['message']}")
            return create_error_response(
                error="Помилка оновлення популярності",
                details=str(result)
            )

    except Exception as e:
        logger.error(f"[API] ❌ Критична помилка оновлення популярності: {e}", exc_info=True)
        return create_error_response(
            error="Критична помилка оновлення популярності",
            details=str(e)
        )


@router.get("/coingecko/popularity/{symbol}")
async def get_coin_popularity(symbol: str):
    """
    Отримує рейтинг популярності конкретної монети.

    Args:
        symbol: Символ монети (BTC, ETH, тощо)

    Returns:
        dict: Інформація про популярність монети
    """
    try:
        rank = await coingecko_service.get_popularity_rank(symbol)

        if rank is not None:
            return {
                "success": True,
                "message": f"Рейтинг популярності для {symbol.upper()}",
                "data": {
                    "symbol": symbol.upper(),
                    "market_cap_rank": rank,
                    "is_popular": rank <= 100  # Топ-100 вважаємо популярними
                },
                "timestamp": datetime.now(UTC).isoformat()
            }
        else:
            return create_error_response(
                error=f"Монета {symbol} не знайдена в рейтингу популярності"
            )

    except Exception as e:
        logger.error(f"[API] Помилка отримання популярності для {symbol}: {e}")
        return create_error_response(
            error="Помилка отримання популярності",
            details=str(e)
        )


@router.get("/coingecko/popularity-stats")
async def get_popularity_stats():
    """
    Отримує статистику по даним популярності монет.

    Returns:
        dict: Статистика популярності
    """
    try:
        stats = await coingecko_service.get_popularity_stats()

        return {
            "success": True,
            "message": "Статистика популярності монет",
            "data": stats,
            "timestamp": datetime.now(UTC).isoformat()
        }

    except Exception as e:
        logger.error(f"[API] Помилка отримання статистики популярності: {e}")
        return create_error_response(
            error="Помилка отримання статистики популярності",
            details=str(e)
        )

@router.get("/coingecko/trending")
async def get_trending_cryptocurrencies():
    """
    Отримує список trending cryptocurrencies з CoinGecko.

    Returns:
        dict: Список trending криптовалют
    """
    try:
        trending_coins = await coingecko_service.get_trending_coins()

        return {
            "success": True,
            "message": f"Отримано {len(trending_coins)} trending cryptocurrencies",
            "data": {
                "trending_coins": trending_coins,
                "total_count": len(trending_coins)
            },
            "timestamp": datetime.now(UTC).isoformat()
        }

    except Exception as e:
        logger.error(f"[API] Помилка отримання trending cryptocurrencies: {e}")
        return create_error_response(
            error="Помилка отримання trending cryptocurrencies",
            details=str(e)
        )

@router.get("/coingecko/trending/{symbol}")
async def get_coin_trending_score(symbol: str):
    """
    Отримує trending score конкретної монети.

    Args:
        symbol: Символ монети (BTC, ETH, тощо)

    Returns:
        dict: Інформація про trending score монети
    """
    try:
        score = await coingecko_service.get_trending_score(symbol)

        if score is not None:
            return {
                "success": True,
                "message": f"Trending score для {symbol.upper()}",
                "data": {
                    "symbol": symbol.upper(),
                    "trending_score": score,
                    "is_trending": score > 0
                },
                "timestamp": datetime.now(UTC).isoformat()
            }
        else:
            return {
                "success": True,
                "message": f"Монета {symbol.upper()} не знаходиться в trending",
                "data": {
                    "symbol": symbol.upper(),
                    "trending_score": None,
                    "is_trending": False
                },
                "timestamp": datetime.now(UTC).isoformat()
            }

    except Exception as e:
        logger.error(f"[API] Помилка отримання trending score для {symbol}: {e}")
        return create_error_response(
            error="Помилка отримання trending score",
            details=str(e)
        )

@router.get("/coingecko/trending-stats")
async def get_trending_stats():
    """
    Отримує статистику по trending cryptocurrencies.

    Returns:
        dict: Статистика trending
    """
    try:
        stats = await coingecko_service.get_trending_stats()

        return {
            "success": True,
            "message": "Статистика trending cryptocurrencies",
            "data": stats,
            "timestamp": datetime.now(UTC).isoformat()
        }

    except Exception as e:
        logger.error(f"[API] Помилка отримання trending статистики: {e}")
        return create_error_response(
            error="Помилка отримання trending статистики",
            details=str(e)
        )


# =============================================================================
# POPULARITY SORTING ENDPOINTS
# =============================================================================

@router.get("/products/popular", response_model=YieldResponse)
async def get_products_sorted_by_popularity(
    limit: int = Query(default=100, ge=1, le=500, description="Кількість продуктів (макс 500)"),
    offset: int = Query(default=0, ge=0, description="Зміщення для пагінації"),
    db: AsyncSession = Depends(get_database_session)
) -> YieldResponse:
    """
    Отримати всі продукти відсортовані за популярністю монет з CoinGecko.

    Продукти сортуються за рейтингом популярності (market_cap_rank) з CoinGecko API.
    Популярні монети (BTC, ETH, тощо) будуть відображатися вище.
    Для монет без рейтингу використовується fallback рейтинг 9999.

    Args:
        limit: Кількість продуктів для повернення
        offset: Зміщення для пагінації
        db: Сесія бази даних

    Returns:
        YieldResponse: Продукти відсортовані за популярністю
    """
    try:
        logger.info(f"🔥 Запит продуктів відсортованих за популярністю: limit={limit}, offset={offset}")

        # Отримуємо продукти відсортовані за популярністю
        from app.db.crud import get_products_sorted_by_popularity
        products = await get_products_sorted_by_popularity(
            limit=limit,
            offset=offset
        )
        logger.info(f"🔥 Отримано {len(products)} продуктів з CRUD")

        # Конвертуємо в модель відповіді
        yield_products = []
        for product in products:
            try:
                yield_product = YieldProduct(
                    id=product.id,
                    symbol=product.symbol,
                    name=product.name,
                    provider=product.provider,
                    apy=float(product.apy),
                    is_cefi=product.is_cefi,
                    min_amount=float(product.min_amount or 0.0),
                    max_amount=float(product.max_amount or 0.0) if product.max_amount else None,
                    lock_period_days=product.lock_period_days,
                    product_type=getattr(product, 'product_type', None),
                    category=getattr(product, 'category', None),
                    is_active=product.is_active,
                    website_url=product.website_url,
                    description=product.description,
                    risk_level=product.risk_level
                )
                yield_products.append(yield_product)
            except Exception as conv_error:
                logger.warning(f"Помилка конвертації продукту {product.id}: {conv_error}")
                continue

        logger.info(f"✅ Повертаємо {len(yield_products)} продуктів відсортованих за популярністю")

        return YieldResponse(
            success=True,
            data=yield_products,
            count=len(yield_products),
            message=f"Продукти відсортовані за популярністю монет (CoinGecko TOP)",
            cached=False,
            source="database_popularity_sorted"
        )

    except Exception as e:
        logger.error(f"[API] Помилка отримання продуктів за популярністю: {e}", exc_info=True)
        return YieldResponse(
            success=False,
            data=[],
            count=0,
            message=f"Помилка отримання продуктів: {str(e)}",
            cached=False,
            source="error"
        )


@router.get("/exchanges/{exchange}/popular", response_model=YieldResponse)
async def get_exchange_products_sorted_by_popularity(
    exchange: str,
    limit: int = Query(default=50, ge=1, le=1000, description="Кількість продуктів (макс 1000)"),
    db: AsyncSession = Depends(get_database_session)
) -> YieldResponse:
    """
    Отримати продукти конкретної біржі відсортовані за популярністю монет.

    Args:
        exchange: Назва біржі (binance, bybit)
        limit: Кількість продуктів для повернення
        db: Сесія бази даних

    Returns:
        YieldResponse: Продукти біржі відсортовані за популярністю
    """
    try:
        # Валідація назви біржі
        exchange_lower = exchange.lower().strip()
        if exchange_lower not in ["binance", "bybit", "okx", "mexc", "bitmart", "gate", "bitget", "kraken", "kucoin", "htx"]:
            raise HTTPException(
                status_code=400,
                detail=f"Непідтримувана біржа '{exchange}'. Доступні: binance, bybit, okx, mexc, bitmart, gate, bitget, kraken, kucoin, htx"
            )

        # Конвертуємо в правильний регістр для бази даних
        provider_mapping = {
            'binance': 'Binance',
            'bybit': 'Bybit',
            'okx': 'OKX',
            'mexc': 'MEXC',
            'bitmart': 'BitMart',
            'gate': 'gate',
            'bitget': 'bitget',
            'kraken': 'Kraken',
            'kucoin': 'KuCoin',
            'htx': 'htx'
        }
        provider_db = provider_mapping.get(exchange_lower, exchange_lower.title())

        logger.info(f"🔥 Запит продуктів {exchange_lower} відсортованих за популярністю: limit={limit}")

        # Отримуємо продукти біржі відсортовані за популярністю
        logger.info(f"🔥 Викликаємо CRUD для провайдера: {provider_db}")
        from app.db.crud import get_products_by_provider_sorted_by_popularity
        products = await get_products_by_provider_sorted_by_popularity(
            provider=provider_db,
            limit=limit
        )
        logger.info(f"🔥 Отримано {len(products)} продуктів з CRUD для {exchange_lower}")

        # Конвертуємо в модель відповіді
        logger.info(f"🔄 Конвертуємо {len(products)} продуктів в модель відповіді")
        yield_products = []
        converted_count = 0
        for product in products:
            try:
                yield_product = YieldProduct(
                    id=product.id,
                    symbol=product.symbol,
                    name=product.name,
                    provider=product.provider,
                    apy=float(product.apy),
                    is_cefi=product.is_cefi,
                    min_amount=float(product.min_amount or 0.0),
                    max_amount=float(product.max_amount or 0.0) if product.max_amount else None,
                    lock_period_days=product.lock_period_days,
                    product_type=getattr(product, 'product_type', None),
                    category=getattr(product, 'category', None),
                    is_active=product.is_active,
                    website_url=product.website_url,
                    description=product.description,
                    risk_level=product.risk_level
                )
                yield_products.append(yield_product)
                converted_count += 1
            except Exception as conv_error:
                logger.warning(f"❌ Помилка конвертації продукту {product.id}: {conv_error}")
                continue

        logger.info(f"✅ Конвертовано {converted_count}/{len(products)} продуктів")
        logger.info(f"✅ Повертаємо {len(yield_products)} продуктів {exchange_lower} за популярністю")

        return YieldResponse(
            success=True,
            data=yield_products,
            count=len(yield_products),
            message=f"Продукти {exchange_lower} відсортовані за популярністю монет",
            cached=False,
            source=f"database_{exchange_lower}_popularity_sorted"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[API] Помилка отримання продуктів {exchange} за популярністю: {e}", exc_info=True)
        return YieldResponse(
            success=False,
            data=[],
            count=0,
            message=f"Помилка отримання продуктів {exchange}: {str(e)}",
            cached=False,
            source="error"
        )


# =============================================================================
# MEXC Manual Import Endpoints
# =============================================================================

@router.post("/mexc/import", response_model=dict, tags=["mexc"])
async def import_mexc_products(import_data: dict):
    """
    Імпорт MEXC продуктів з JSON.
    
    MEXC не має публічного API, тому продукти завантажуються вручну.
    
    Request body:
    {
      "exchange": "MEXC",
      "updated_at": "2025-10-30T12:00:00Z",
      "products": [
        {
          "product_type": "Flexible",
          "symbol": "BTC",
          "apy": 2.5,
          "min_amount": 0.001,
          "max_amount": null,
          "lock_period_days": 0,
          "status": "active"
        }
      ]
    }
    """
    try:
        from app.services.exchanges.mexc.models import MEXCManualImport
        
        # Валідація через Pydantic
        validated_data = MEXCManualImport(**import_data)
        
        if validated_data.exchange.upper() != "MEXC":
            raise HTTPException(status_code=400, detail="exchange має бути 'MEXC'")
        
        # Імпорт продуктів
        created_count = 0
        updated_count = 0
        errors = []
        
        async with get_database_session() as db:
            for product in validated_data.products:
                try:
                    # Генерація ID
                    if product.lock_period_days == 0:
                        product_id = f"mexc_flexible_{product.symbol.lower()}"
                    else:
                        product_id = f"mexc_locked_{product.symbol.lower()}_{product.lock_period_days}"
                    
                    # Підготовка даних для БД
                    product_data = YieldProductCreate(
                        id=product_id,
                        symbol=product.symbol.upper(),
                        name=f"{product.symbol.upper()} {product.product_type} Savings" + (
                            f" ({product.lock_period_days} days)" if product.lock_period_days > 0 else ""
                        ),
                        provider="MEXC",
                        apy=product.apy,
                        min_amount=product.min_amount or 0.0,
                        max_amount=product.max_amount,
                        lock_period_days=product.lock_period_days,
                        product_type=product.product_type,
                        is_active=(product.status.lower() == "active"),
                        risk_level="Low" if product.product_type == "Flexible" else "Medium",
                        description=f"MEXC {product.product_type} Savings for {product.symbol}",
                        website_url="https://www.mexc.com/staking",
                        raw_data=product.dict()
                    )
                    
                    # Upsert в БД
                    existing = await YieldProductCRUD.get_product_by_id(db, product_id)
                    if existing:
                        await YieldProductCRUD.update_product(db, product_id, product_data.dict(exclude_unset=True))
                        updated_count += 1
                    else:
                        await YieldProductCRUD.create_product(db, product_data)
                        created_count += 1
                        
                except Exception as e:
                    errors.append(f"{product.symbol}: {str(e)}")
                    logger.error(f"Помилка імпорту продукту {product.symbol}: {e}")
            
            # Commit змін
            await db.commit()
        
        result = {
            "success": True,
            "created": created_count,
            "updated": updated_count,
            "total": len(validated_data.products),
            "errors": errors,
            "imported_at": datetime.now(UTC).isoformat()
        }
        
        logger.info(f"MEXC імпорт завершено: {created_count} створено, {updated_count} оновлено")
        return result
        
    except Exception as e:
        logger.error(f"Помилка імпорту MEXC: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Помилка імпорту: {str(e)}")


@router.get("/mexc/test", response_model=dict, tags=["mexc"])
async def test_mexc_connection():
    """Тест підключення MEXC (перевірка БД)."""
    from app.services.exchanges.mexc.service import MEXCService
    service = MEXCService()
    result = await service.test_connection()
    return result


@router.get("/mexc/products", response_model=YieldResponse, tags=["mexc"])
async def get_mexc_products(
    symbol: Optional[str] = Query(default=None, description="Фільтр по символу"),
    limit: Optional[int] = Query(default=100, description="Ліміт продуктів")
):
    """Отримання MEXC продуктів з БД."""
    from app.services.exchanges.mexc.service import MEXCService
    service = MEXCService()
    products = await service.get_products_with_cache(symbol=symbol)
    
    if limit:
        products = products[:limit]
    
    return create_success_response(products)


@router.post("/mexc/sync", response_model=dict, tags=["mexc"])
async def sync_mexc_products(symbol: Optional[str] = Query(default=None, description="Синхронізувати тільки певний символ")):
    """Синхронізація MEXC продуктів в БД."""
    try:
        from app.services.exchanges.mexc.service import MEXCService
        service = MEXCService()
        result = await service.sync_products_to_db(symbol=symbol)
        return {
            "success": result.get("status") == "success",
            "status": result.get("status"),
            "message": result.get("message"),
            "created": result.get("sync_stats", {}).get("created", 0),
            "updated": result.get("sync_stats", {}).get("updated", 0),
            "deleted": result.get("sync_stats", {}).get("deleted", 0),
            "total": result.get("sync_stats", {}).get("total", 0),
            "data": result
        }
    except Exception as e:
        logger.error(f"❌ Помилка синхронізації MEXC: {e}")
        return {
            "success": False,
            "status": "error",
            "message": f"Помилка синхронізації: {str(e)}"
        }


# =============================================================================
# GATE.IO ENDPOINTS
# =============================================================================

@router.get("/gate/test", response_model=dict, tags=["gate"])
async def test_gate_connection():
    """Тестування підключення до Gate.io API."""
    try:
        gate_service = exchange_registry.get_exchange_service("gate")
        result = await gate_service.test_connection()
        return {
            "success": True,
            "status": "success",
            "message": "Тест підключення до Gate.io API виконано",
            "data": result
        }

    except Exception as e:
        logger.error(f"❌ Помилка тестування Gate.io API: {e}")
        return create_error_response(
            error="Помилка тестування Gate.io API",
            details=str(e)
        )


@router.get("/gate/products", response_model=YieldResponse, tags=["gate"])
async def get_gate_products(
    symbol: Optional[str] = Query(None, description="Фільтр по символу"),
    limit: Optional[int] = Query(default=100, description="Ліміт продуктів")
):
    """Отримати продукти Gate.io з кешуванням."""
    try:
        gate_service = exchange_registry.get_exchange_service("gate")
        products_data = await gate_service.get_products_with_cache(symbol)

        # Конвертуємо в YieldProduct моделі
        yield_products = []
        for item in products_data:
            try:
                product = YieldProduct(**item)
                yield_products.append(product)
            except Exception as e:
                logger.warning(f"⚠️ Помилка конвертації продукту Gate.io: {e}")

        return create_success_response(
            data=yield_products,
            message=f"Отримано {len(yield_products)} продуктів Gate.io",
            cached=True
        )

    except Exception as e:
        logger.error(f"❌ Помилка отримання продуктів Gate.io: {e}")
        return create_error_response(
            error="Помилка отримання продуктів Gate.io",
            details=str(e)
        )


@router.get("/exchanges/gate/products", response_model=YieldResponse, tags=["gate"])
async def get_gate_exchange_products(
    symbol: Optional[str] = Query(None, description="Фільтр по символу"),
    limit: Optional[int] = Query(default=100, description="Ліміт продуктів")
):
    """Альтернативний endpoint для Gate.io продуктів (для сумісності з Telegram ботом)."""
    return await get_gate_products(symbol=symbol, limit=limit)


@router.get("/exchanges/gate/popular", response_model=YieldResponse, tags=["gate"])
async def get_gate_popular(limit: Optional[int] = Query(default=10, description="Ліміт продуктів")):
    """Отримати популярні продукти Gate.io (топ за APY)."""
    try:
        gate_service = exchange_registry.get_exchange_service("gate")
        all_products = await gate_service.get_products_with_cache()

        # Конвертуємо в YieldProduct та сортуємо за APY
        yield_products = []
        for item in all_products:
            try:
                product = YieldProduct(**item)
                yield_products.append(product)
            except Exception as e:
                logger.warning(f"⚠️ Помилка конвертації продукту: {e}")

        # Сортуємо за APY (спадання) і беремо топ
        sorted_products = sorted(yield_products, key=lambda p: p.apy, reverse=True)
        top_products = sorted_products[:limit]

        return create_success_response(
            data=top_products,
            message=f"Топ {len(top_products)} продуктів Gate.io за APY"
        )

    except Exception as e:
        logger.error(f"❌ Помилка отримання популярних Gate.io: {e}")
        return create_error_response(
            error="Помилка отримання популярних Gate.io",
            details=str(e)
        )


@router.post("/gate/sync", response_model=dict, tags=["gate"])
async def sync_gate_products(
    symbol: Optional[str] = Query(None, description="Синхронізувати тільки конкретний символ")
):
    """Синхронізувати продукти Gate.io з API в БД."""
    try:
        gate_service = exchange_registry.get_exchange_service("gate")
        result = await gate_service.sync_products_to_db(symbol)

        if result["status"] == "success":
            return {
                "success": True,
                "status": "success",
                "message": f"Синхронізація Gate.io завершена: {result['sync_stats']['created']} створено, {result['sync_stats']['updated']} оновлено",
                "data": result
            }
        else:
            return create_error_response(
                error=result.get("message", "Помилка синхронізації"),
                details=str(result)
            )

    except Exception as e:
        logger.error(f"❌ Помилка синхронізації Gate.io: {e}")
        return create_error_response(
            error="Помилка синхронізації Gate.io",
            details=str(e)
        )


@router.post("/gate/import", response_model=dict, tags=["gate"])
async def import_gate_fixed_products(import_data: dict):
    """
    Імпорт Gate.io Fixed продуктів з JSON.
    
    Gate.io не має публічного API для Fixed Savings, тому продукти завантажуються вручну.
    
    Request body:
    {
      "exchange": "Gate.io",
      "updated_at": "2025-10-30T12:00:00Z",
      "products": [
        {
          "product_type": "Fixed",
          "symbol": "USDT",
          "apy": 6.5,
          "min_amount": 10,
          "max_amount": null,
          "lock_period_days": 30,
          "status": "active"
        }
      ]
    }
    """
    try:
        if import_data.get("exchange", "").lower() != "gate":
            raise HTTPException(status_code=400, detail="exchange має бути 'gate'")
        
        products_list = import_data.get("products", [])
        if not products_list:
            raise HTTPException(status_code=400, detail="products не може бути порожнім")
        
        # Імпорт продуктів
        created_count = 0
        updated_count = 0
        errors = []
        
        async with get_database_session() as db:
            for product in products_list:
                try:
                    symbol = product.get("symbol", "").upper()
                    lock_days = product.get("lock_period_days", 0)
                    product_type = product.get("product_type", "Fixed")
                    
                    # Генерація ID
                    if lock_days == 0:
                        product_id = f"gate_flexible_{symbol.lower()}"
                    else:
                        product_id = f"gate_fixed_{symbol.lower()}_{lock_days}"
                    
                    # Підготовка даних для БД
                    product_data = YieldProductCreate(
                        id=product_id,
                        symbol=symbol,
                        name=f"{symbol} {product_type} Savings" + (
                            f" ({lock_days} days)" if lock_days > 0 else ""
                        ),
                        provider="gate",
                        apy=float(product.get("apy", 0)),
                        min_amount=product.get("min_amount") or 0.0,
                        max_amount=product.get("max_amount"),
                        lock_period_days=lock_days,
                        product_type=product_type,
                        is_active=(product.get("status", "active").lower() == "active"),
                        risk_level="Low",
                        description=f"Gate.io {product_type} Savings for {symbol}",
                        website_url="https://www.gate.com/simple-earn",
                        raw_data=product
                    )
                    
                    # Upsert в БД
                    existing = await YieldProductCRUD.get_product_by_id(db, product_id)
                    if existing:
                        await YieldProductCRUD.update_product(db, product_id, product_data.dict(exclude_unset=True))
                        updated_count += 1
                    else:
                        await YieldProductCRUD.create_product(db, product_data)
                        created_count += 1
                        
                except Exception as e:
                    errors.append(f"{symbol}: {str(e)}")
                    logger.error(f"Помилка імпорту продукту {symbol}: {e}")
            
            # Commit змін
            await db.commit()
        
        result = {
            "success": True,
            "created": created_count,
            "updated": updated_count,
            "total": len(products_list),
            "errors": errors,
            "imported_at": datetime.now(UTC).isoformat()
        }
        
        logger.info(f"Gate.io імпорт завершено: {created_count} створено, {updated_count} оновлено")
        return result
        
    except Exception as e:
        logger.error(f"Помилка імпорту Gate.io: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Помилка імпорту: {str(e)}")


@router.get("/gate/health", response_model=dict, tags=["gate"])
async def get_gate_health():
    """Перевірити стан Gate.io сервісу."""
    try:
        gate_service = exchange_registry.get_exchange_service("gate")
        health_info = await gate_service.get_health_status()
        return {
            "success": True,
            "status": "success",
            "message": "Стан Gate.io сервісу перевірено",
            "data": health_info
        }

    except Exception as e:
        logger.error(f"❌ Помилка перевірки Gate.io сервісу: {e}")
        return create_error_response(
            error="Помилка перевірки Gate.io сервісу",
            details=str(e)
        )


# =============================================================================
# BITGET ENDPOINTS
# =============================================================================

@router.get("/bitget/test", response_model=dict, tags=["bitget"])
async def test_bitget_connection():
    """Тест підключення до Bitget API."""
    try:
        from app.services.exchanges.bitget.service import BitgetService
        service = BitgetService()
        await service.initialize()
        result = await service.test_connection()
        return {
            "success": result.get("status") == "success",
            "status": result.get("status"),
            "message": result.get("message"),
            "data": result
        }
    except Exception as e:
        logger.error(f"❌ Помилка тесту Bitget: {e}")
        return {
            "success": False,
            "status": "error",
            "message": f"Помилка тесту підключення: {str(e)}"
        }


@router.post("/bitget/sync", response_model=dict, tags=["bitget"])
async def sync_bitget_products():
    """Синхронізація Bitget продуктів в БД."""
    try:
        from app.services.exchanges.bitget.service import BitgetService
        service = BitgetService()
        await service.initialize()
        result = await service.sync_products_to_db()
        return {
            "success": result.get("status") == "success",
            "status": result.get("status"),
            "message": result.get("message"),
            "data": result
        }
    except Exception as e:
        logger.error(f"❌ Помилка синхронізації Bitget: {e}")
        return {
            "success": False,
            "status": "error",
            "message": f"Помилка синхронізації: {str(e)}"
        }


@router.get("/bitget/health", response_model=dict, tags=["bitget"])
async def get_bitget_health():
    """Перевірити стан Bitget сервісу."""
    try:
        bitget_service = exchange_registry.get_exchange_service("bitget")
        health_info = await bitget_service.get_health_status()
        return {
            "success": True,
            "status": "success",
            "message": "Стан Bitget сервісу перевірено",
            "data": health_info
        }
    except Exception as e:
        logger.error(f"❌ Помилка перевірки Bitget сервісу: {e}")
        return create_error_response(
            error="Помилка перевірки Bitget сервісу",
            details=str(e)
        )


# =============================================================================
# Kraken endpoints
# =============================================================================

@router.get("/kraken/test")
async def test_kraken_connection():
    """Тестування підключення до Kraken API."""
    try:
        kraken_service = exchange_registry.get_exchange_service("kraken")
        result = await kraken_service.test_connection()
        return {
            "success": True,
            "status": "success",
            "message": "Тест підключення до Kraken API виконано",
            "data": result
        }
        
    except Exception as e:
        logger.error(f"❌ Помилка тестування Kraken API: {e}")
        return create_error_response(
            error="Помилка тестування Kraken API",
            details=str(e)
        )


@router.get("/kraken/products")
async def get_kraken_products(symbol: Optional[str] = Query(None, description="Фільтр по символу")):
    """Отримати продукти Kraken з кешуванням."""
    try:
        kraken_service = exchange_registry.get_exchange_service("kraken")
        products_data = await kraken_service.get_products_with_cache(symbol)
        
        # Конвертуємо в YieldProduct моделі
        yield_products = []
        for item in products_data:
            try:
                product = YieldProduct(**item)
                yield_products.append(product)
            except Exception as e:
                logger.warning(f"⚠️ Помилка конвертації продукту Kraken: {e}")
        
        return create_success_response(
            data=yield_products,
            message=f"Отримано {len(yield_products)} продуктів Kraken",
            cached=True  # Завжди з кешу через сервіс
        )
        
    except Exception as e:
        logger.error(f"❌ Помилка отримання продуктів Kraken: {e}")
        return create_error_response(
            error="Помилка отримання продуктів Kraken",
            details=str(e)
        )


@router.post("/kraken/sync")
async def sync_kraken_products(
    symbol: Optional[str] = Query(None, description="Синхронізувати тільки конкретний символ")
):
    """Синхронізувати продукти Kraken з API в БД."""
    try:
        kraken_service = exchange_registry.get_exchange_service("kraken")
        result = await kraken_service.sync_products_to_db(symbol)
        
        if result["status"] == "success":
            return {
                "success": True,
                "status": "success",
                "message": f"Синхронізація Kraken завершена: {result['sync_stats']['created']} створено, {result['sync_stats']['updated']} оновлено",
                "data": result
            }
        else:
            return create_error_response(
                error=result.get("message", "Помилка синхронізації"),
                details=str(result)
            )
            
    except Exception as e:
        logger.error(f"❌ Помилка синхронізації Kraken продуктів: {e}")
        return create_error_response(
            error="Помилка синхронізації Kraken",
            details=str(e)
        )


@router.get("/kraken/test-strategies")
async def test_kraken_strategies():
    """Тестує різні варіанти отримання Kraken Earn стратегій."""
    try:
        kraken_service = exchange_registry.get_exchange_service("kraken")
        result = await kraken_service.api_client.test_different_strategies()
        return {
            "success": True,
            "status": "success",
            "message": "Тестування стратегій завершено",
            "data": [result],  # Обгортаємо в list для валідації
            "timestamp": datetime.now(UTC).isoformat()
        }
    except Exception as e:
        logger.error(f"❌ Помилка тестування стратегій Kraken: {e}")
        return create_error_response(
            error="Помилка тестування стратегій",
            details=str(e)
        )


@router.get("/kraken/test-endpoints")
async def test_kraken_endpoints():
    """Тестує інші приватні ендпоінти Kraken API."""
    try:
        kraken_service = exchange_registry.get_exchange_service("kraken")
        result = await kraken_service.api_client.test_other_endpoints()
        return {
            "success": True,
            "status": "success",
            "message": "Тестування ендпоінтів завершено",
            "data": [result],  # Обгортаємо в list для валідації
            "timestamp": datetime.now(UTC).isoformat()
        }
    except Exception as e:
        logger.error(f"❌ Помилка тестування ендпоінтів Kraken: {e}")
        return create_error_response(
            error="Помилка тестування ендпоінтів",
            details=str(e)
        )


@router.get("/kraken/test-get-products")
async def test_kraken_get_products():
    """Тестує отримання продуктів через get_earn_products."""
    try:
        kraken_service = exchange_registry.get_exchange_service("kraken")
        result = await kraken_service.api_client.get_earn_products()
        return {
            "success": True,
            "status": "success",
            "message": f"Отримано {len(result)} продуктів",
            "data": result,
            "timestamp": datetime.now(UTC).isoformat()
        }
    except Exception as e:
        logger.error(f"❌ Помилка тестування get_earn_products Kraken: {e}")
        return create_error_response(
            error="Помилка тестування get_earn_products",
            details=str(e)
        )


@router.post("/kraken/sync-direct")
async def sync_kraken_direct():
    """Пряма синхронізація продуктів Kraken без кешу."""
    try:
        kraken_service = exchange_registry.get_exchange_service("kraken")

        # Отримуємо продукти напряму з API
        logger.info("🔄 Пряма синхронізація Kraken - отримуємо продукти з API...")
        products = await kraken_service.api_client.get_earn_products()
        logger.info(f"✅ Отримано {len(products)} продуктів з API")

        if not products:
            return create_error_response(
                error="Продукти не знайдено в API",
                details="API повернув порожній список продуктів"
            )

        # Нормалізуємо
        normalized_products = await kraken_service._normalize_products(products)
        logger.info(f"✅ Нормалізовано {len(normalized_products)} продуктів")

        # Зберігаємо в БД
        sync_stats = await kraken_service._save_products_to_db(normalized_products)
        logger.info(f"✅ Збережено в БД: {sync_stats}")

        return {
            "success": True,
            "status": "success",
            "message": f"Синхронізація завершена: {sync_stats['created']} створено, {sync_stats['updated']} оновлено",
            "data": {
                "api_products": len(products),
                "normalized_products": len(normalized_products),
                "sync_stats": sync_stats
            },
            "timestamp": datetime.now(UTC).isoformat()
        }

    except Exception as e:
        logger.error(f"❌ Помилка прямої синхронізації Kraken: {e}")
        return create_error_response(
            error="Помилка прямої синхронізації",
            details=str(e)
        )


@router.get("/kraken/test-aggregation")
async def test_kraken_aggregation():
    """Тест агрегації продуктів Kraken."""
    try:
        from app.services.aggregation_service import aggregation_service
        data, sources, calls = await aggregation_service._get_exchange_data("kraken", None, "kraken")
        return {
            "success": True,
            "status": "success",
            "message": f"Агрегація повернула {len(data)} продуктів",
            "data": {
                "products_count": len(data),
                "sources": [s.value for s in sources],
                "api_calls": calls,
                "first_product": data[0] if data else None
            },
            "timestamp": datetime.now(UTC).isoformat()
        }
    except Exception as e:
        logger.error(f"❌ Помилка тестування агрегації Kraken: {e}")
        return create_error_response(
            error="Помилка тестування агрегації",
            details=str(e)
        )


# =============================================================================
# PRIORITY PRODUCTS ENDPOINTS
# =============================================================================

@router.get("/priority-products/{exchange}")
async def get_priority_products(
    exchange: str = Path(..., description="Назва біржі (binance, bybit)")
):
    """
    Отримати основні продукти (BTC, ETH, SOL, USDT) для біржі.
    
    Завжди повертає 4 продукти в правильному порядку: BTC, ETH, SOL, USDT.
    Якщо продукт не знайдено - повертає з APY=0.0.
    
    Args:
        exchange: Назва біржі (binance, bybit, okx, mexc, bitmart, gate, bitget, kraken, kucoin, htx)
        db: Сесія бази даних
        
    Returns:
        dict: Список з 4 продуктів в порядку BTC, ETH, SOL, USDT
    """
    try:
        # Валідація назви біржі
        exchange_lower = exchange.lower().strip()
        valid_exchanges = [
            "binance", "bybit", "okx", "mexc", "bitmart", 
            "gate", "bitget", "kraken", "kucoin", "htx"
        ]
        
        if exchange_lower not in valid_exchanges:
            return create_error_response(
                error=f"Непідтримувана біржа '{exchange}'",
                details=f"Доступні: {', '.join(valid_exchanges)}"
            )
        
        # Отримуємо priority продукти
        from app.db.database import db_manager
        async with db_manager.get_session() as db:
            products = await PriorityProductCRUD.get_priority_products_by_exchange(
                db, exchange_lower
            )
        
        logger.info(f"📊 Отримано {len(products)} priority продуктів для {exchange_lower}")
        
        # Конвертуємо в словники для відповіді
        products_data = []
        for product in products:
            # Перевіряємо чи це реальний об'єкт з БД (має id) чи fallback
            has_id = hasattr(product, 'id') and product.id is not None
            logger.debug(f"  {product.symbol}: APY={product.apy}, is_active={product.is_active}, has_id={has_id}")
            
            products_data.append({
                "symbol": product.symbol,
                "apy": float(product.apy),
                "is_active": product.is_active,
                "product_id": product.product_id,
                "lock_period_days": product.lock_period_days,
                "exchange": product.exchange,
                "updated_at": product.updated_at.isoformat() if product.updated_at else None
            })
        
        # Повертаємо простий dict без валідації через YieldResponse
        return {
            "success": True,
            "status": "success",
            "data": products_data,
            "count": len(products_data),
            "message": f"Отримано {len(products_data)} priority продуктів для {exchange_lower}",
            "cached": False,
            "source": "priority_products_table",
            "timestamp": datetime.now(UTC).isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Помилка отримання priority продуктів для {exchange}: {e}")
        return create_error_response(
            error="Помилка отримання priority продуктів",
            details=str(e)
        )


@router.post("/priority-products/update")
async def update_priority_products(
    exchange: Optional[str] = Query(None, description="Оновити тільки для конкретної біржі (якщо не вказано - для всіх)")
):
    """
    Оновити priority_products з даних yield_products.
    
    Для кожної біржі та символу (BTC, ETH, SOL, USDT):
    - Знаходить найкращий flexible продукт (найвищий APY, lock_period_days=0)
    - Оновлює або створює запис в priority_products з актуальним APY
    
    Args:
        exchange: Опціональна назва біржі (binance, bybit, etc.)
        
    Returns:
        dict: Статистика оновлення
    """
    try:
        from app.services.priority_products_service import priority_products_service
        from app.db.database import db_manager
        
        async with db_manager.get_session() as db:
            if exchange:
                # Оновлюємо тільки для конкретної біржі
                count = await priority_products_service.update_priority_products_for_exchange(
                    db, exchange.lower()
                )
                stats = {exchange.lower(): count, "total": count}
            else:
                # Оновлюємо для всіх бірж
                stats = await priority_products_service.update_all_exchanges(db)
            
            logger.info(f"✅ Priority products оновлено: {stats}")
            
            return {
                "success": True,
                "status": "success",
                "message": f"Priority products оновлено: {stats.get('total', 0)} продуктів",
                "data": stats
            }
            
    except Exception as e:
        logger.error(f"❌ Помилка оновлення priority_products: {e}", exc_info=True)
        return create_error_response(
            error="Помилка оновлення priority_products",
            details=str(e)
        )


# =============================================================================
# ПОКРАЩЕНА ВАЛІДАЦІЯ - оновлено існуючі endpoints
# =============================================================================

# Експортуємо роутери для імпорту в main.py
__all__ = ["router", "metrics_router"]
