from fastapi import Response

from fastapi import APIRouter, Depends, HTTPException, Query, Path
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, text
from typing import List, Optional, Dict, Any
from datetime import datetime, UTC

from app.db.database import get_database_session, get_db_transaction
from app.db.crud import (
    YieldProductCRUD,
    ExchangeDataCRUD,
    CacheMetadataCRUD,
    PriorityProductCRUD,
    get_database_stats,
)
from app.db.models import YieldProductDB, CoinsPopularityDB, TopProductDB
from app.models.yield_product import YieldProduct, YieldProductFilter, YieldProductCreate
from app.models.response import (
    YieldResponse,
    TopByProviderResponse,
    ErrorResponse,
    create_success_response,
    create_error_response,
    HealthResponse,
    StatsResponse,
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
    trigger_health_check,
)
from app.utils.logger import logger
from app.__version__ import __version__


from app.api.dependencies import protect_operations

router = APIRouter(prefix="/api/v1", tags=["yield"], dependencies=[Depends(protect_operations)])


metrics_router = APIRouter(tags=["metrics"])


@router.get("/yield/batch")
async def get_yield_batch(
    symbols: str = Query(..., description=""),
    limit: Optional[int] = Query(default=20, ge=1, le=100, description=""),
    db: AsyncSession = Depends(get_database_session),
):
    try:
        symbol_list = [s.strip().upper() for s in symbols.split(",") if s.strip()]

        if not symbol_list:
            return create_error_response(
                error="Не вказано символів",
                details="Параметр symbols повинен містити принаймні один символ",
            )

        if len(symbol_list) > 20:
            return create_error_response(
                error="Занадто багато символів", details="Максимум 20 символів за один запит"
            )

        logger.info(
            f"🔄 Batch запит yield продуктів для {len(symbol_list)} символів: {symbol_list}"
        )

        result_data = {}
        total_count = 0

        for symbol in symbol_list:
            try:
                aggregation_result = await aggregation_service.aggregate_yield_data(
                    symbol=symbol, limit=limit or 20, strategy=AggregationStrategy.COMPREHENSIVE
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
            "message": f"Отримано дані для {len(symbol_list)} символів",
        }

    except Exception as e:
        logger.error(f"❌ Помилка batch запиту: {e}")
        return create_error_response(error="Помилка batch запиту", details=str(e))


@router.get("/yield/{symbol}", response_model=YieldResponse)
async def get_yield_by_symbol(
    symbol: str = Path(..., description="", min_length=2, max_length=10),
    limit: int = Query(default=50, ge=1, le=100, description=""),
    min_apy: Optional[float] = Query(default=None, ge=0, le=1000, description=""),
    provider: Optional[str] = Query(default=None, description=""),
    db: AsyncSession = Depends(get_database_session),
) -> YieldResponse:
    try:
        symbol_upper = symbol.upper().strip()

        if not symbol_upper.isalnum():
            raise HTTPException(
                status_code=400, detail="Символ повинен містити тільки літери та цифри"
            )

        logger.info(f"🔄 Запит yield продуктів для {symbol_upper} через сервіс агрегації")

        aggregation_result = await aggregation_service.aggregate_yield_data(
            symbol=symbol_upper,
            limit=limit,
            min_apy=min_apy,
            provider=provider,
            strategy=AggregationStrategy.COMPREHENSIVE,
        )

        providers_in_result = (
            [p.provider for p in aggregation_result.data[:10]] if aggregation_result.data else []
        )
        sources_used_str = ", ".join([s.value for s in aggregation_result.sources_used])

        logger.info(
            f"📊 Агрегація завершена: {len(aggregation_result.data)} продуктів з джерел [{sources_used_str}]"
        )
        logger.info(
            f"🔍 Провайдери в результаті: {providers_in_result} | "
            f"Час: {aggregation_result.total_response_time_ms:.2f}мс | "
            f"Якість: {aggregation_result.data_quality_score:.2f}"
        )

        if aggregation_result.errors_encountered:
            logger.warning(f"⚠️ Помилки під час агрегації: {aggregation_result.errors_encountered}")

        primary_source = "aggregated"
        if aggregation_result.sources_used:
            if len(aggregation_result.sources_used) == 1:
                primary_source = aggregation_result.sources_used[0].value
            else:
                primary_source = "combined"

        from_cache = (
            len(aggregation_result.sources_used) == 1
            and aggregation_result.sources_used[0] == DataSource.CACHE
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
                "provider": provider,
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Помилка отримання yield продуктів для {symbol}: {e}")
        raise HTTPException(status_code=500, detail=f"Внутрішня помилка сервера: {str(e)}")


@router.get("/top", response_model=TopByProviderResponse)
async def get_top_yields(
    limit: int = Query(default=10, ge=1, le=50, description=""),
) -> TopByProviderResponse:
    try:
        cache_key = f"top_by_provider_{limit}"
        logger.info(f"📊 Запит топ {limit} yield продуктів по кожній біржі")

        cached_data = await cache_manager.get_cached_data(cache_key)
        if cached_data is not None:
            logger.info(f"🎯 Топ продукти по provider'ам отримано з кешу")

            yield_products_by_provider = {}
            for provider, products_data in cached_data["data"].items():
                yield_products_by_provider[provider] = [
                    YieldProduct(**item) for item in products_data
                ]

            return TopByProviderResponse(
                success=True,
                data=yield_products_by_provider,
                total_count=cached_data["total_count"],
                providers_count=cached_data["providers_count"],
                cached=True,
                source="cache",
                message=f"Знайдено {cached_data['total_count']} топ продуктів по {cached_data['providers_count']} біржам (з кешу)",
            )

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
                    message="Топ продукти не знайдено",
                )

            yield_products_by_provider = {}
            total_converted = 0

            for provider, products in products_by_provider.items():
                provider_products = []
                for product in products:
                    try:
                        try:

                            def safe_float(value, default=0.0):
                                if value is None:
                                    return default
                                try:
                                    return float(value)
                                except (ValueError, TypeError):
                                    logger.warning(
                                        f"⚠️ Неможливо конвертувати в float: {value} ({type(value)}) для продукту {product.id}"
                                    )
                                    return default

                            def safe_int(value, default=0):
                                if value is None:
                                    return default
                                try:
                                    return int(float(value))
                                except (ValueError, TypeError):
                                    logger.warning(
                                        f"⚠️ Неможливо конвертувати в int: {value} ({type(value)}) для продукту {product.id}"
                                    )
                                    return default

                            min_amount = safe_float(product.min_amount, 0.0)
                            max_amount = (
                                safe_float(product.max_amount, None)
                                if product.max_amount is not None
                                else None
                            )
                            apy = safe_float(product.apy, 0.0)
                            max_apy = (
                                safe_float(product.max_apy, None)
                                if product.max_apy is not None
                                else None
                            )
                            lock_period_days = safe_int(product.lock_period_days, 0)

                        except Exception as type_error:
                            logger.warning(
                                f"⚠️ Критична помилка конвертації типів для продукту {product.id}: {type_error}"
                            )

                            continue

                        yield_product = YieldProduct(
                            id=product.id,
                            symbol=product.symbol,
                            name=product.name,
                            provider=product.provider,
                            apy=apy,
                            is_cefi=product.is_cefi,
                            min_amount=min_amount,
                            max_amount=max_amount,
                            lock_period_days=lock_period_days,
                            max_apy=max_apy,
                            risk_level=product.risk_level,
                            is_active=product.is_active,
                            website_url=product.website_url,
                            description=product.description,
                            created_at=product.created_at,
                            updated_at=product.updated_at,
                            last_checked=product.last_checked,
                            raw_data=product.raw_data,
                        )
                        provider_products.append(yield_product)
                        total_converted += 1
                    except Exception as e:
                        logger.error(
                            f"❌ Помилка конвертації продукту {product.id} від {provider}: {e}",
                            exc_info=True,
                        )

                        try:
                            logger.debug(
                                f"🔍 Деталі продукту {product.id}: apy={product.apy} ({type(product.apy)}), min_amount={product.min_amount} ({type(product.min_amount)}), max_amount={product.max_amount} ({type(product.max_amount)}), lock_period_days={product.lock_period_days} ({type(product.lock_period_days)})"
                            )
                        except Exception as debug_error:
                            logger.error(
                                f"❌ Помилка діагностики продукту {product.id}: {debug_error}"
                            )
                        continue

                if provider_products:
                    yield_products_by_provider[provider] = provider_products

            logger.info(
                f"✅ Знайдено {total_converted} топ продуктів по {len(yield_products_by_provider)} біржам"
            )

            cache_data = {
                "data": {
                    provider: [product.model_dump() for product in products]
                    for provider, products in yield_products_by_provider.items()
                },
                "total_count": total_converted,
                "providers_count": len(yield_products_by_provider),
                "timestamp": datetime.now(UTC).isoformat(),
            }
            await cache_manager.set_cached_data(cache_key, cache_data)

            return TopByProviderResponse(
                success=True,
                data=yield_products_by_provider,
                total_count=total_converted,
                providers_count=len(yield_products_by_provider),
                cached=False,
                source="database",
                message=f"Топ продукти по {len(yield_products_by_provider)} біржам",
            )
    except Exception as e:
        logger.error(f"❌ Помилка отримання топ продуктів: {e}")
        raise HTTPException(status_code=500, detail=f"Внутрішня помилка сервера: {str(e)}")


@router.get("/products", response_model=YieldResponse)
async def get_all_products(
    limit: int = Query(default=100, ge=1, le=5000, description=""),
    offset: int = Query(default=0, ge=0, description=""),
    symbol: Optional[str] = Query(default=None, description=""),
    provider: Optional[str] = Query(default=None, description=""),
    min_apy: Optional[float] = Query(default=None, ge=0, description=""),
    max_apy: Optional[float] = Query(default=None, ge=0, description=""),
    sort_by: Optional[str] = Query(default="popularity", description=""),
    lock_period_days: Optional[int] = Query(default=None, description=""),
    db: AsyncSession = Depends(get_database_session),
) -> YieldResponse:
    try:
        logger.info(
            f"📋 Запит всіх продуктів з фільтрами: symbol={symbol}, provider={provider}, min_apy={min_apy}, max_apy={max_apy}, lock_period_days={lock_period_days}, sort_by={sort_by}"
        )

        filters = YieldProductFilter(
            symbol=symbol,
            provider=provider,
            min_apy=min_apy,
            max_apy=max_apy,
            lock_period_days=lock_period_days,
        )
        logger.info(f"📋 Створено фільтри: {filters.dict(exclude_none=True)}")

        if sort_by == "popularity":
            logger.info(f"📋 Сортування за популярністю через Python-side sorting")
            try:
                if any([symbol, provider, min_apy, max_apy, lock_period_days is not None]):
                    products = await YieldProductCRUD.filter_products(filters, limit=None)
                    logger.info(
                        f"📊 Отримано {len(products) if products else 0} відфільтрованих продуктів для сортування за популярністю"
                    )
                else:
                    products = await YieldProductCRUD.get_all_products(limit=None, offset=0)
                    logger.info(
                        f"📊 Отримано {len(products) if products else 0} всіх продуктів для сортування за популярністю"
                    )

                if products:
                    popularity_data = {}
                    try:
                        popularity_records = await YieldProductCRUD.get_all_coins_popularity()
                        popularity_data = {
                            p.symbol.upper(): p.market_cap_rank for p in popularity_records
                        }
                        logger.info(
                            f"📊 Отримано дані про популярність для {len(popularity_data)} монет"
                        )
                    except Exception as e:
                        logger.warning(f"⚠️ Не вдалося отримати дані про популярність: {e}")

                    def sort_key(product):
                        symbol_upper = product.symbol.upper()
                        popularity_rank = popularity_data.get(symbol_upper, 9999)
                        return (popularity_rank, -product.apy, product.id)

                    products.sort(key=sort_key)
                    logger.info(
                        f"🐍 Продукти відсортовані за популярністю в Python (перші 10: {[p.symbol for p in products[:10]]})"
                    )

                    start_idx = offset or 0
                    end_idx = start_idx + (limit or len(products))
                    products = products[start_idx:end_idx]
                    logger.info(
                        f"📊 Повертаємо {len(products)} продуктів після пагінації (offset={start_idx}, limit={limit})"
                    )

                logger.info(
                    f"📊 Python-side sorting повернув {len(products) if products else 0} продуктів"
                )
            except Exception as e:
                logger.error(
                    f"❌ Помилка Python-side сортування за популярністю: {e}", exc_info=True
                )

                products = await YieldProductCRUD.filter_products(filters, limit, offset)
        elif any([symbol, provider, min_apy, max_apy, lock_period_days is not None]):
            logger.info(
                f"📋 Фільтрація продуктів через filter_products: symbol={symbol}, provider={provider}, min_apy={min_apy}, max_apy={max_apy}, lock_period_days={lock_period_days}"
            )
            products = await YieldProductCRUD.filter_products(filters)
            logger.info(f"📋 filter_products повернув {len(products) if products else 0} продуктів")
        else:
            logger.info(
                f"📋 Отримання всіх продуктів через get_all_products: limit={limit}, offset={offset}"
            )
            products = await YieldProductCRUD.get_all_products(limit, offset)
            logger.info(
                f"📋 get_all_products повернув {len(products) if products else 0} продуктів"
            )

        logger.info(f"📋 Знайдено {len(products) if products else 0} продуктів в БД")

        if sort_by and sort_by != "popularity" and products:
            if sort_by == "apy_desc":
                products.sort(key=lambda x: x.apy, reverse=True)
                logger.info("📋 Продукти відсортовані за APY (від більшого)")
            elif sort_by == "apy_asc":
                products.sort(key=lambda x: x.apy)
                logger.info("📋 Продукти відсортовані за APY (від меншого)")

        if not products:
            logger.warning(
                f"⚠️ Продукти не знайдено в БД. Фільтри: symbol={symbol}, provider={provider}, min_apy={min_apy}, max_apy={max_apy}, lock_period_days={lock_period_days}, sort_by={sort_by}"
            )

            try:
                total_count = await db.execute(
                    select(func.count(YieldProductDB.id)).where(YieldProductDB.is_active == True)
                )
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
                message="Продукти не знайдено",
            )

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
                    raw_data=product.raw_data,
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
            source="database",
        )

    except Exception as e:
        logger.error(f"❌ Помилка отримання продуктів: {e}")
        raise HTTPException(status_code=500, detail=f"Внутрішня помилка сервера: {str(e)}")


@router.get("/stats", response_model=StatsResponse)
async def get_database_statistics():
    try:
        logger.info("📊 Запит статистики бази даних")

        from app.db.database import db_manager

        if not db_manager.session_factory or not db_manager.engine:
            logger.warning("⚠️ БД недоступна для статистики - не ініціалізована")

            cache_stats = await cache_manager.get_cache_stats()
            return StatsResponse(
                success=True,
                total_products=0,
                active_products=0,
                providers_count=0,
                symbols_count=0,
                cache_hit_rate=cache_stats.get("hit_rate_percent", 0),
                last_updated=datetime.now(UTC),
            )

        from app.db.database import get_db_transaction

        async with get_db_transaction() as db:
            stats = await get_database_stats(db)

            logger.info("✅ Статистика отримана з БД")
            return StatsResponse(
                success=True,
                total_products=stats.get("total_products", 0),
                active_products=stats.get("total_products", 0),
                providers_count=stats.get("providers_count", 0),
                symbols_count=stats.get("symbols_count", 0),
                cache_hit_rate=stats.get("hit_rate_percent", 0),
                last_updated=datetime.now(UTC),
            )

    except Exception as e:
        logger.error(f"❌ Помилка отримання статистики: {e}")

        try:
            cache_stats = await cache_manager.get_cache_stats()
            return StatsResponse(
                success=True,
                total_products=0,
                active_products=0,
                providers_count=0,
                symbols_count=0,
                cache_hit_rate=cache_stats.get("hit_rate_percent", 0),
                last_updated=datetime.now(UTC),
            )
        except Exception as cache_error:
            logger.error(f"❌ Помилка cache статистики: {cache_error}")
            raise HTTPException(status_code=500, detail=f"Внутрішня помилка сервера: {str(e)}")


@router.post("/products", response_model=YieldResponse)
async def create_yield_product(
    product_data: YieldProductCreate, db: AsyncSession = Depends(get_db_transaction)
) -> YieldResponse:
    try:
        logger.info(f"➕ Створення нового продукту: {product_data.symbol}")

        created_product = await YieldProductCRUD.create_product(db, product_data)

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
            raw_data=created_product.raw_data,
        )

        logger.info(f"✅ Продукт {created_product.id} створено")
        return create_success_response(
            data=[yield_product],
            message=f"Продукт {created_product.symbol} створено",
            cached=False,
            source="database",
        )

    except Exception as e:
        logger.error(f"❌ Помилка створення продукту: {e}")
        raise HTTPException(status_code=500, detail=f"Внутрішня помилка сервера: {str(e)}")


@router.get("/health", response_model=HealthResponse)
async def health_check_detailed() -> HealthResponse:
    try:
        db_status = "unhealthy"
        try:
            async with get_database_session() as db:
                await db.execute(text("SELECT 1"))
                db_status = "healthy"
                logger.info("✅ БД healthy (SELECT 1 успішно)")
        except Exception as e:
            logger.warning(f"⚠️ Помилка перевірки БД: {e}")
            db_status = "unhealthy"

        try:
            cache_health = await cache_manager.health_check()
            cache_status = cache_health.get("status", "unknown")
        except Exception as e:
            logger.warning(f"⚠️ Помилка перевірки кешу: {e}")
            cache_status = "degraded"

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
            api_status={"binance": binance_status, "bybit": bybit_status},
        )

    except Exception as e:
        logger.error(f"❌ Помилка health check: {e}")
        return HealthResponse(
            success=False,
            service="yield-data-service",
            version=__version__,
            database_status="unhealthy",
            cache_status="unknown",
            api_status={"error": str(e)},
        )


@router.get("/cache/stats")
async def get_cache_stats():
    try:
        stats = await cache_manager.get_cache_stats()
        return {
            "success": True,
            "status": "success",
            "message": "Статистика кешу отримана успішно",
            "data": stats,
        }

    except Exception as e:
        logger.error(f"❌ Помилка отримання статистики кешу: {e}")
        return create_error_response(error="Помилка отримання статистики кешу", details=str(e))


@router.post("/cache/clear")
async def clear_cache(pattern: str = "*"):
    try:
        deleted_count = await cache_manager.clear_cache(pattern)
        return {
            "success": True,
            "status": "success",
            "message": f"Кеш очищено: видалено {deleted_count} ключів",
            "data": {"deleted_count": deleted_count, "pattern": pattern},
        }

    except Exception as e:
        logger.error(f"❌ Помилка очищення кешу: {e}")
        return create_error_response(error="Помилка очищення кешу", details=str(e))


@router.get("/cache/health")
async def get_cache_health():
    try:
        health_info = await cache_manager.health_check()
        return {
            "success": True,
            "status": "success",
            "message": "Стан кешу перевірено",
            "data": health_info,
        }

    except Exception as e:
        logger.error(f"❌ Помилка перевірки кешу: {e}")
        return create_error_response(error="Помилка перевірки кешу", details=str(e))


# =============================================================================
# BINANCE API ENDPOINTS
# =============================================================================


@router.get("/binance/test")
async def test_binance_connection():
    try:
        binance_service = exchange_registry.get_exchange_service("binance")
        result = await binance_service.test_connection()
        return {
            "success": True,
            "status": "success",
            "message": "Тест підключення до Binance API виконано",
            "data": result,
        }

    except Exception as e:
        logger.error(f"❌ Помилка тестування Binance API: {e}")
        return create_error_response(error="Помилка тестування Binance API", details=str(e))


@router.get("/binance/products")
async def get_binance_products(symbol: Optional[str] = Query(None, description="")):
    try:
        binance_service = exchange_registry.get_exchange_service("binance")
        products_data = await binance_service.get_products_with_cache(symbol)

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
            cached=True,
        )

    except Exception as e:
        logger.error(f"❌ Помилка отримання продуктів Binance: {e}")
        return create_error_response(error="Помилка отримання продуктів Binance", details=str(e))


@router.post("/binance/sync")
async def sync_binance_products(symbol: Optional[str] = Query(None, description="")):
    try:
        binance_service = exchange_registry.get_exchange_service("binance")
        result = await binance_service.sync_products_to_db(symbol)

        if result["status"] == "success":
            return {
                "success": True,
                "status": "success",
                "message": f"Синхронізація Binance завершена: {result['sync_stats']['created']} створено, {result['sync_stats']['updated']} оновлено",
                "data": result,
            }
        else:
            return create_error_response(
                error=result.get("message", "Помилка синхронізації"), details=str(result)
            )

    except Exception as e:
        logger.error(f"❌ Помилка синхронізації Binance: {e}")
        return create_error_response(error="Помилка синхронізації Binance", details=str(e))


@router.get("/binance/health")
async def get_binance_health():
    try:
        binance_service = exchange_registry.get_exchange_service("binance")
        health_info = await binance_service.get_health_status()
        return {
            "success": True,
            "status": "success",
            "message": "Стан Binance сервісу перевірено",
            "data": health_info,
        }

    except Exception as e:
        logger.error(f"❌ Помилка перевірки Binance сервісу: {e}")
        return create_error_response(error="Помилка перевірки Binance сервісу", details=str(e))


# =============================================================================
# BYBIT API ENDPOINTS
# =============================================================================


@router.get("/bybit/test")
async def test_bybit_connection():
    try:
        bybit_service = exchange_registry.get_exchange_service("bybit")
        result = await bybit_service.test_connection()
        return {
            "success": True,
            "status": "success",
            "message": "Тест підключення до Bybit API виконано",
            "data": result,
        }

    except Exception as e:
        logger.error(f"❌ Помилка тестування Bybit API: {e}")
        return create_error_response(error="Помилка тестування Bybit API", details=str(e))


@router.get("/bybit/products")
async def get_bybit_products(symbol: Optional[str] = Query(None, description="")):
    try:
        bybit_service = exchange_registry.get_exchange_service("bybit")
        products_data = await bybit_service.get_products_with_cache(symbol)

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
            cached=True,
        )

    except Exception as e:
        logger.error(f"❌ Помилка отримання продуктів Bybit: {e}")
        return create_error_response(error="Помилка отримання продуктів Bybit", details=str(e))


@router.post("/bybit/test-full")
async def test_bybit_full_products():
    try:
        bybit_service = exchange_registry.get_exchange_service("bybit")

        if hasattr(bybit_service, "api_client") and bybit_service.api_client:
            products = await bybit_service.api_client.get_earn_products()
        else:
            from app.services.exchanges.bybit.api import BybitAPI

            api_client = BybitAPI("", "")
            products = await api_client.get_earn_products()
        return {
            "success": True,
            "message": f"Отримано {len(products)} продуктів",
            "count": len(products),
            "products": products[:5],
        }
    except Exception as e:
        logger.error(f"❌ Помилка тестування Bybit: {e}")
        return create_error_response(error="Помилка тестування Bybit", details=str(e))


@router.post("/bybit/sync")
async def sync_bybit_products(symbol: Optional[str] = Query(None, description="")):
    try:
        bybit_service = exchange_registry.get_exchange_service("bybit")
        result = await bybit_service.sync_products_to_db(symbol)

        if result["status"] == "success":
            return {
                "success": True,
                "status": "success",
                "message": f"Синхронізація Bybit завершена: {result['sync_stats']['created']} створено, {result['sync_stats']['updated']} оновлено",
                "data": result,
            }
        else:
            return create_error_response(
                error=result.get("message", "Помилка синхронізації"), details=str(result)
            )

    except Exception as e:
        logger.error(f"❌ Помилка синхронізації Bybit: {e}")
        return create_error_response(error="Помилка синхронізації Bybit", details=str(e))


@router.get("/bybit/health")
async def get_bybit_health():
    try:
        bybit_service = exchange_registry.get_exchange_service("bybit")
        health_info = await bybit_service.get_health_status()
        return {
            "success": True,
            "status": "success",
            "message": "Стан Bybit сервісу перевірено",
            "data": health_info,
        }

    except Exception as e:
        logger.error(f"❌ Помилка перевірки Bybit сервісу: {e}")
        return create_error_response(error="Помилка перевірки Bybit сервісу", details=str(e))


# =============================================================================
# BITMART API ENDPOINTS
# =============================================================================


@router.post("/bitmart/sync")
async def sync_bitmart_products(symbol: Optional[str] = Query(None, description="")):
    try:
        bitmart_service = exchange_registry.get_exchange_service("bitmart")
        result = await bitmart_service.sync_products_to_db(symbol)

        if result.get("status") == "success":
            return {
                "success": True,
                "status": "success",
                "message": f"Синхронізація BitMart завершена: {result['sync_stats']['created']} створено, {result['sync_stats']['updated']} оновлено",
                "data": result,
            }
        else:
            return create_error_response(
                error=result.get("message", "Помилка синхронізації"), details=str(result)
            )

    except Exception as e:
        logger.error(f"❌ Помилка синхронізації BitMart: {e}")
        return create_error_response(error="Помилка синхронізації BitMart", details=str(e))


@router.get("/bitmart/health")
async def get_bitmart_health():
    try:
        bitmart_service = exchange_registry.get_exchange_service("bitmart")
        health_info = await bitmart_service.get_health_status()
        return {
            "success": True,
            "status": "success",
            "message": "Стан BitMart сервісу перевірено",
            "data": health_info,
        }

    except Exception as e:
        logger.error(f"❌ Помилка перевірки BitMart сервісу: {e}")
        return create_error_response(error="Помилка перевірки BitMart сервісу", details=str(e))


# =============================================================================
# HTX API ENDPOINTS
# =============================================================================


@router.post("/htx/sync")
async def sync_htx_products(symbol: Optional[str] = Query(None, description="")):
    try:
        htx_service = exchange_registry.get_exchange_service("htx")
        result = await htx_service.sync_products_to_db(symbol)

        if result.get("status") == "success":
            return {
                "success": True,
                "status": "success",
                "message": f"Синхронізація HTX завершена: {result['sync_stats']['created']} створено, {result['sync_stats']['updated']} оновлено",
                "data": result,
            }
        else:
            return create_error_response(
                error=result.get("message", "Помилка синхронізації"), details=str(result)
            )

    except Exception as e:
        logger.error(f"❌ Помилка синхронізації HTX: {e}")
        return create_error_response(error="Помилка синхронізації HTX", details=str(e))


@router.get("/htx/health")
async def get_htx_health():
    try:
        htx_service = exchange_registry.get_exchange_service("htx")
        health_info = await htx_service.get_health_status()
        return {
            "success": True,
            "status": "success",
            "message": "Стан HTX сервісу перевірено",
            "data": health_info,
        }

    except Exception as e:
        logger.error(f"❌ Помилка перевірки HTX сервісу: {e}")
        return create_error_response(error="Помилка перевірки HTX сервісу", details=str(e))


@router.get("/htx/products", response_model=YieldResponse)
async def get_htx_products_from_db(
    limit: int = Query(default=1000, ge=1, le=1000, description=""),
    db: AsyncSession = Depends(get_database_session),
) -> YieldResponse:
    try:
        logger.info(f"🔥 Запит HTX продуктів з бази даних (limit={limit})")

        from app.db.crud import YieldProductCRUD

        products = await YieldProductCRUD.get_products_by_provider_with_popularity_sorting(
            db, "HTX", limit
        )

        product_dicts = []
        for product in products:
            product_dict = {
                "id": product.id,
                "symbol": product.symbol,
                "name": product.name,
                "provider": product.provider,
                "apy": float(product.apy),
                "is_cefi": product.is_cefi,
                "min_amount": float(product.min_amount) if product.min_amount else 0.0,
                "max_amount": float(product.max_amount) if product.max_amount else None,
                "lock_period_days": product.lock_period_days,
                "max_apy": float(product.max_apy) if product.max_apy else None,
                "risk_level": product.risk_level,
                "is_active": product.is_active,
                "website_url": product.website_url,
                "description": product.description,
                "product_type": product.product_type,
                "created_at": product.created_at.isoformat() if product.created_at else None,
                "updated_at": product.updated_at.isoformat() if product.updated_at else None,
                "last_checked": product.last_checked.isoformat() if product.last_checked else None,
                "raw_data": product.raw_data,
            }
            product_dicts.append(product_dict)

        logger.info(f"✅ Отримано {len(product_dicts)} HTX продуктів з бази даних")

        return YieldResponse(
            success=True,
            data=product_dicts,
            count=len(product_dicts),
            cached=False,
            source="htx_db",
            message=f"Знайдено {len(product_dicts)} HTX продуктів з бази даних",
        )

    except Exception as e:
        logger.error(f"❌ Помилка отримання HTX продуктів з БД: {e}")
        raise HTTPException(status_code=500, detail=f"Внутрішня помилка сервера: {str(e)}")


# =============================================================================
# OKX API ENDPOINTS
# =============================================================================


@router.get("/okx/test")
async def test_okx_connection():
    try:
        okx_service = exchange_registry.get_exchange_service("okx")
        result = await okx_service.test_connection()
        return {
            "success": True,
            "status": "success",
            "message": "Тест підключення до OKX API виконано",
            "data": result,
        }

    except Exception as e:
        logger.error(f"❌ Помилка тестування OKX API: {e}")
        return create_error_response(error="Помилка тестування OKX API", details=str(e))


@router.get("/okx/products")
async def get_okx_products(symbol: Optional[str] = Query(None, description="")):
    try:
        okx_service = exchange_registry.get_exchange_service("okx")
        products_data = await okx_service.get_products_with_cache(symbol)

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
            cached=True,
        )

    except Exception as e:
        logger.error(f"❌ Помилка отримання продуктів OKX: {e}")
        return create_error_response(error="Помилка отримання продуктів OKX", details=str(e))


@router.post("/okx/sync")
async def sync_okx_products(symbol: Optional[str] = Query(None, description="")):
    try:
        okx_service = exchange_registry.get_exchange_service("okx")
        result = await okx_service.sync_products_to_db(symbol)

        if result["status"] == "success":
            return {
                "success": True,
                "status": "success",
                "message": f"Синхронізація OKX завершена: {result['sync_stats']['created']} створено, {result['sync_stats']['updated']} оновлено",
                "data": result,
            }
        else:
            return create_error_response(
                error=result.get("message", "Помилка синхронізації"), details=str(result)
            )

    except Exception as e:
        logger.error(f"❌ Помилка синхронізації OKX: {e}")
        return create_error_response(error="Помилка синхронізації OKX", details=str(e))


@router.get("/okx/health")
async def get_okx_health():
    try:
        okx_service = exchange_registry.get_exchange_service("okx")
        health_info = await okx_service.get_health_status()
        return {
            "success": True,
            "status": "success",
            "message": "Стан OKX сервісу перевірено",
            "data": health_info,
        }

    except Exception as e:
        logger.error(f"❌ Помилка перевірки OKX сервісу: {e}")
        return create_error_response(error="Помилка перевірки OKX сервісу", details=str(e))


# =============================================================================
# KUCOIN API ENDPOINTS
# =============================================================================


@router.get("/kucoin/test")
async def test_kucoin_connection():
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
async def get_kucoin_products(symbol: Optional[str] = Query(None, description="")):
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
async def sync_kucoin_products(symbol: Optional[str] = Query(None, description="")):
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

# =============================================================================


@router.get("/exchanges")
async def get_exchange_data(
    exchange: Optional[str] = Query(None, description=""),
    symbol: Optional[str] = Query(None, description=""),
    limit: int = Query(default=500, ge=1, le=1000, description=""),
    db: AsyncSession = Depends(get_database_session),
):

    if exchange is None:
        try:
            exchanges_status = {}

            # Binance
            try:
                binance_service = exchange_registry.get_exchange_service("binance")
                binance_health = await binance_service.get_health_status()
                exchanges_status["binance"] = {
                    "name": "Binance",
                    "status": "healthy"
                    if binance_health.get("status") == "healthy"
                    else "degraded",
                    "description": "Криптобіржа Binance - найбільша у світі",
                    "endpoints": [
                        "/api/v1/exchanges?exchange=binance",
                        "/api/v1/binance/products",
                        "/api/v1/binance/test",
                    ],
                }
            except Exception as e:
                exchanges_status["binance"] = {
                    "name": "Binance",
                    "status": "unhealthy",
                    "error": str(e),
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
                        "/api/v1/bybit/test",
                    ],
                }
            except Exception as e:
                exchanges_status["bybit"] = {
                    "name": "Bybit",
                    "status": "unhealthy",
                    "error": str(e),
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
                        "/api/v1/okx/test",
                    ],
                }
            except Exception as e:
                exchanges_status["okx"] = {"name": "OKX", "status": "unhealthy", "error": str(e)}

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
                        "/api/v1/kucoin/test",
                    ],
                }
            except Exception as e:
                exchanges_status["kucoin"] = {
                    "name": "KuCoin",
                    "status": "unhealthy",
                    "error": str(e),
                }

            return {
                "success": True,
                "exchanges": exchanges_status,
                "total_exchanges": len(exchanges_status),
                "message": "Список доступних бірж отримано",
            }
        except Exception as e:
            logger.error(f"❌ Помилка отримання списку бірж: {e}")
            raise HTTPException(status_code=500, detail=f"Внутрішня помилка сервера: {str(e)}")
    try:
        exchange_lower = exchange.lower().strip()
        if exchange_lower not in [
            "binance",
            "bybit",
            "okx",
            "mexc",
            "bitmart",
            "gate",
            "bitget",
            "kraken",
            "kucoin",
            "htx",
        ]:
            raise HTTPException(
                status_code=400,
                detail=f"Непідтримувана біржа '{exchange}'. Доступні: binance, bybit, okx, mexc, bitmart, gate, bitget, kraken, kucoin, htx",
            )

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
            "htx": "htx",
        }

        provider_name = provider_mapping.get(exchange_lower, exchange_lower)

        logger.info(
            f"🏦 Запит даних з біржі {exchange_lower} (provider: {provider_name}) через сервіс агрегації"
        )

        aggregation_result = await aggregation_service.aggregate_yield_data(
            symbol=symbol,
            limit=limit,
            provider=provider_name,
            strategy=AggregationStrategy.COMPREHENSIVE,
        )

        logger.info(
            f"📊 Агрегація {exchange_lower}: {len(aggregation_result.data)} продуктів, "
            f"джерела: {[s.value for s in aggregation_result.sources_used]}, "
            f"API виклики: {aggregation_result.api_calls_made}, "
            f"час: {aggregation_result.total_response_time_ms:.2f}мс"
        )

        if aggregation_result.errors_encountered:
            logger.warning(
                f"⚠️ Помилки під час агрегації {exchange_lower}: {aggregation_result.errors_encountered}"
            )

        from_cache = any(source == DataSource.CACHE for source in aggregation_result.sources_used)

        return YieldResponse(
            success=True,
            data=aggregation_result.data,
            count=len(aggregation_result.data),
            cached=from_cache,
            source=f"{exchange_lower}_aggregated",
            message=f"Знайдено {len(aggregation_result.data)} продуктів з {exchange_lower} (якість: {aggregation_result.data_quality_score:.2f})",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Помилка отримання даних з {exchange}: {e}")
        raise HTTPException(status_code=500, detail=f"Внутрішня помилка сервера: {str(e)}")


@router.get("/exchanges/list")
async def get_available_exchanges():
    try:
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
                    "/api/v1/binance/test",
                ],
            }
        except Exception as e:
            exchanges_status["binance"] = {
                "name": "Binance",
                "status": "unhealthy",
                "error": str(e),
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
                    "/api/v1/bybit/test",
                ],
            }
        except Exception as e:
            exchanges_status["bybit"] = {"name": "Bybit", "status": "unhealthy", "error": str(e)}

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
                    "/api/v1/okx/test",
                ],
            }
        except Exception as e:
            exchanges_status["okx"] = {"name": "OKX", "status": "unhealthy", "error": str(e)}

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
                    "/api/v1/kucoin/test",
                ],
            }
        except Exception as e:
            exchanges_status["kucoin"] = {"name": "KuCoin", "status": "unhealthy", "error": str(e)}

        return {
            "success": True,
            "exchanges": exchanges_status,
            "total_exchanges": len(exchanges_status),
            "message": "Список доступних бірж отримано",
        }

    except Exception as e:
        logger.error(f"❌ Помилка отримання списку бірж: {e}")
        raise HTTPException(status_code=500, detail=f"Внутрішня помилка сервера: {str(e)}")


# =============================================================================

# =============================================================================


@router.get("/aggregation/stats")
async def get_aggregation_stats():
    try:
        stats = await aggregation_service.get_aggregation_stats()
        return {
            "success": True,
            "status": "success",
            "message": "Статистика сервісу агрегації отримана",
            "data": stats,
        }

    except Exception as e:
        logger.error(f"❌ Помилка отримання статистики агрегації: {e}")
        return create_error_response(error="Помилка отримання статистики агрегації", details=str(e))


@router.get("/aggregation/test")
async def test_aggregation(
    symbol: Optional[str] = Query(None, description=""),
    strategy: str = Query(default="fast_cache_first", description=""),
    limit: int = Query(default=10, ge=1, le=50, description=""),
):
    try:
        try:
            strategy_enum = AggregationStrategy(strategy)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Невірна стратегія '{strategy}'. Доступні: fast_cache_first, comprehensive, fallback_chain",
            )

        logger.info(f"🧪 Тестування агрегації: символ={symbol}, стратегія={strategy}")

        start_time = datetime.now(UTC)
        result = await aggregation_service.aggregate_yield_data(
            symbol=symbol, limit=limit, strategy=strategy_enum
        )
        end_time = datetime.now(UTC)

        test_report = {
            "test_config": {"symbol": symbol, "strategy": strategy, "limit": limit},
            "aggregation_result": {
                "products_found": len(result.data),
                "sources_used": [s.value for s in result.sources_used],
                "cache_hits": result.cache_hits,
                "cache_misses": result.cache_misses,
                "api_calls_made": result.api_calls_made,
                "errors_encountered": result.errors_encountered,
                "total_response_time_ms": result.total_response_time_ms,
                "data_quality_score": result.data_quality_score,
            },
            "test_duration_ms": (end_time - start_time).total_seconds() * 1000,
            "timestamp": end_time.isoformat(),
        }

        logger.info(
            f"✅ Тест агрегації завершено: {len(result.data)} продуктів за {test_report['test_duration_ms']:.2f}мс"
        )

        return {
            "success": True,
            "status": "success",
            "message": f"Тест агрегації завершено успішно: знайдено {len(result.data)} продуктів",
            "data": test_report,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Помилка тестування агрегації: {e}")
        return create_error_response(error="Помилка тестування агрегації", details=str(e))


# =============================================================================

# =============================================================================


@metrics_router.get("/metrics")
async def prometheus_metrics_endpoint():
    try:
        metrics = await get_prometheus_metrics()
        return Response(content=metrics, media_type="text/plain; charset=utf-8")
    except Exception as e:
        logger.error(f"❌ Помилка генерації Prometheus метрик: {e}")
        return Response(
            content="# Error generating metrics\n", media_type="text/plain; charset=utf-8"
        )


# =============================================================================

# =============================================================================


@router.get("/scheduler/status")
async def get_scheduler_status_endpoint():
    try:
        status = await get_scheduler_status()
        return {
            "success": True,
            "status": "success",
            "message": "Статус scheduler отримано",
            "data": status,
        }
    except Exception as e:
        logger.error(f"❌ Помилка отримання статусу scheduler: {e}")
        return create_error_response(error="Помилка отримання статусу scheduler", details=str(e))


@router.get("/scheduler/metrics")
async def get_scheduler_metrics_endpoint():
    try:
        metrics = await get_scheduler_metrics()
        return {
            "success": True,
            "status": "success",
            "message": "Метрики scheduler отримано",
            "data": metrics,
        }
    except Exception as e:
        logger.error(f"❌ Помилка отримання метрик scheduler: {e}")
        return create_error_response(error="Помилка отримання метрик scheduler", details=str(e))


@router.post("/scheduler/trigger/cache")
async def trigger_cache_update_endpoint():
    try:
        logger.info("🔄 Ручне оновлення кешу запущено...")
        await trigger_cache_update()
        return {
            "success": True,
            "status": "success",
            "message": "Кеш оновлено вручну",
            "timestamp": datetime.now(UTC).isoformat(),
        }
    except Exception as e:
        logger.error(f"❌ Помилка ручного оновлення кешу: {e}")
        return create_error_response(error="Помилка ручного оновлення кешу", details=str(e))


@router.post("/scheduler/trigger/sync")
async def trigger_db_sync_endpoint():
    try:
        logger.info("🔄 Ручна синхронізація БД запущена...")
        await trigger_db_sync()
        return {
            "success": True,
            "status": "success",
            "message": "БД синхронізовано вручну",
            "timestamp": datetime.now(UTC).isoformat(),
        }
    except Exception as e:
        logger.error(f"❌ Помилка ручної синхронізації БД: {e}")
        return create_error_response(error="Помилка ручної синхронізації БД", details=str(e))


@router.post("/scheduler/trigger/healthcheck")
async def trigger_healthcheck_endpoint():
    try:
        logger.info("🏥 Ручна перевірка здоров'я запущена...")
        await trigger_health_check()
        return {
            "success": True,
            "status": "success",
            "message": "Health check виконано вручну",
            "timestamp": datetime.now(UTC).isoformat(),
        }
    except Exception as e:
        logger.error(f"❌ Помилка ручної перевірки здоров'я: {e}")
        return create_error_response(error="Помилка ручної перевірки здоров'я", details=str(e))


# =============================================================================
# COINGECKO POPULARITY ENDPOINTS
# =============================================================================


@router.post("/coingecko/add-htx-symbols")
async def add_htx_symbols_to_popularity():
    try:
        logger.info("[API] 📊 Початок додавання HTX символів до популярності")

        result = await coingecko_service.add_missing_htx_symbols()

        if result["success"]:
            logger.info(f"[API] ✅ HTX символи додані: {result['message']}")
            return {
                "success": True,
                "message": "HTX символи успішно додані до популярності",
                "data": result,
                "timestamp": datetime.now(UTC).isoformat(),
            }
        else:
            logger.error(f"[API] ❌ Помилка додавання HTX символів: {result['message']}")
            return create_error_response(
                error="Помилка додавання HTX символів", details=str(result)
            )

    except Exception as e:
        logger.error(f"[API] Критична помилка додавання HTX символів: {e}")
        return create_error_response(
            error="Критична помилка додавання HTX символів", details=str(e)
        )


@router.post("/coingecko/update-popularity")
async def update_coins_popularity():
    try:
        logger.info("[API] 📊 Початок оновлення рейтингу популярності монет")

        result = await coingecko_service.update_coins_popularity()

        if result["success"]:
            logger.info(f"[API] ✅ Рейтинг популярності оновлено: {result['message']}")
            return {
                "success": True,
                "message": "Рейтинг популярності успішно оновлено",
                "data": result,
                "timestamp": datetime.now(UTC).isoformat(),
            }
        else:
            logger.error(f"[API] ❌ Помилка оновлення популярності: {result['message']}")
            return create_error_response(
                error="Помилка оновлення популярності", details=str(result)
            )

    except Exception as e:
        logger.error(f"[API] ❌ Критична помилка оновлення популярності: {e}", exc_info=True)
        return create_error_response(
            error="Критична помилка оновлення популярності", details=str(e)
        )


@router.get("/coingecko/popularity/{symbol}")
async def get_coin_popularity(symbol: str):
    try:
        rank = await coingecko_service.get_popularity_rank(symbol)

        if rank is not None:
            return {
                "success": True,
                "message": f"Рейтинг популярності для {symbol.upper()}",
                "data": {
                    "symbol": symbol.upper(),
                    "market_cap_rank": rank,
                    "is_popular": rank <= 100,
                },
                "timestamp": datetime.now(UTC).isoformat(),
            }
        else:
            return create_error_response(
                error=f"Монета {symbol} не знайдена в рейтингу популярності"
            )

    except Exception as e:
        logger.error(f"[API] Помилка отримання популярності для {symbol}: {e}")
        return create_error_response(error="Помилка отримання популярності", details=str(e))


@router.get("/coingecko/popularity-stats")
async def get_popularity_stats():
    try:
        stats = await coingecko_service.get_popularity_stats()

        return {
            "success": True,
            "message": "Статистика популярності монет",
            "data": stats,
            "timestamp": datetime.now(UTC).isoformat(),
        }

    except Exception as e:
        logger.error(f"[API] Помилка отримання статистики популярності: {e}")
        return create_error_response(
            error="Помилка отримання статистики популярності", details=str(e)
        )


@router.get("/coingecko/trending")
async def get_trending_cryptocurrencies():
    try:
        trending_coins = await coingecko_service.get_trending_coins()

        return {
            "success": True,
            "message": f"Отримано {len(trending_coins)} trending cryptocurrencies",
            "data": {"trending_coins": trending_coins, "total_count": len(trending_coins)},
            "timestamp": datetime.now(UTC).isoformat(),
        }

    except Exception as e:
        logger.error(f"[API] Помилка отримання trending cryptocurrencies: {e}")
        return create_error_response(
            error="Помилка отримання trending cryptocurrencies", details=str(e)
        )


@router.get("/coingecko/trending/{symbol}")
async def get_coin_trending_score(symbol: str):
    try:
        score = await coingecko_service.get_trending_score(symbol)

        if score is not None:
            return {
                "success": True,
                "message": f"Trending score для {symbol.upper()}",
                "data": {
                    "symbol": symbol.upper(),
                    "trending_score": score,
                    "is_trending": score > 0,
                },
                "timestamp": datetime.now(UTC).isoformat(),
            }
        else:
            return {
                "success": True,
                "message": f"Монета {symbol.upper()} не знаходиться в trending",
                "data": {"symbol": symbol.upper(), "trending_score": None, "is_trending": False},
                "timestamp": datetime.now(UTC).isoformat(),
            }

    except Exception as e:
        logger.error(f"[API] Помилка отримання trending score для {symbol}: {e}")
        return create_error_response(error="Помилка отримання trending score", details=str(e))


@router.get("/coingecko/trending-stats")
async def get_trending_stats():
    try:
        stats = await coingecko_service.get_trending_stats()

        return {
            "success": True,
            "message": "Статистика trending cryptocurrencies",
            "data": stats,
            "timestamp": datetime.now(UTC).isoformat(),
        }

    except Exception as e:
        logger.error(f"[API] Помилка отримання trending статистики: {e}")
        return create_error_response(error="Помилка отримання trending статистики", details=str(e))


# =============================================================================
# POPULARITY SORTING ENDPOINTS
# =============================================================================


@router.get("/products/popular", response_model=YieldResponse)
async def get_products_sorted_by_popularity(
    limit: int = Query(default=100, ge=1, le=5000, description=""),
    offset: int = Query(default=0, ge=0, description=""),
    db: AsyncSession = Depends(get_database_session),
) -> YieldResponse:
    try:
        logger.info(
            f"🔥 Запит продуктів відсортованих за популярністю: limit={limit}, offset={offset}"
        )

        from app.db.crud import get_products_sorted_by_popularity

        products = await get_products_sorted_by_popularity(limit=limit, offset=offset)
        logger.info(f"🔥 Отримано {len(products)} продуктів з CRUD")

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
                    product_type=getattr(product, "product_type", None),
                    category=getattr(product, "category", None),
                    is_active=product.is_active,
                    website_url=product.website_url,
                    description=product.description,
                    risk_level=product.risk_level,
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
            source="database_popularity_sorted",
        )

    except Exception as e:
        logger.error(f"[API] Помилка отримання продуктів за популярністю: {e}", exc_info=True)
        return YieldResponse(
            success=False,
            data=[],
            count=0,
            message=f"Помилка отримання продуктів: {str(e)}",
            cached=False,
            source="error",
        )


@router.post("/admin/fill-test-popularity", tags=["admin"])
async def fill_test_popularity_data(
    db: AsyncSession = Depends(get_database_session),
) -> Dict[str, Any]:
    try:
        logger.info("🔄 Заповнення тестових даних популярності...")

        test_popularity_data = [
            {"coin_id": "bitcoin", "symbol": "BTC", "market_cap_rank": 1},
            {"coin_id": "ethereum", "symbol": "ETH", "market_cap_rank": 2},
            {"coin_id": "tether", "symbol": "USDT", "market_cap_rank": 3},
            {"coin_id": "binancecoin", "symbol": "BNB", "market_cap_rank": 4},
            {"coin_id": "solana", "symbol": "SOL", "market_cap_rank": 5},
            {"coin_id": "usd-coin", "symbol": "USDC", "market_cap_rank": 6},
            {"coin_id": "cardano", "symbol": "ADA", "market_cap_rank": 7},
            {"coin_id": "dogecoin", "symbol": "DOGE", "market_cap_rank": 8},
            {"coin_id": "polygon", "symbol": "MATIC", "market_cap_rank": 9},
            {"coin_id": "avalanche-2", "symbol": "AVAX", "market_cap_rank": 10},
            {"coin_id": "xinfin", "symbol": "XCN", "market_cap_rank": 100},
            {"coin_id": "injective-protocol", "symbol": "INJ", "market_cap_rank": 101},
            {"coin_id": "usd1", "symbol": "USD1", "market_cap_rank": 102},
        ]

        from app.db.crud import create_or_update_coins_popularity

        created = 0
        updated = 0
        for coin_data in test_popularity_data:
            try:
                await create_or_update_coins_popularity(db, coin_data)
                created += 1
                logger.debug(f"✅ Створено популярність для {coin_data['symbol']}")
            except Exception as e:
                logger.warning(f"⚠️ Помилка створення популярності для {coin_data['symbol']}: {e}")

        logger.info(f"✅ Заповнено {created} тестових записів популярності")
        return {
            "success": True,
            "message": f"Створено {created} тестових записів популярності",
            "records_created": created,
        }

    except Exception as e:
        logger.error(f"❌ Помилка заповнення тестових даних: {e}")
        return {"success": False, "message": str(e), "error": "fill_failed"}


@router.get("/exchanges/{exchange}/popular", response_model=YieldResponse)
async def get_exchange_products_sorted_by_popularity(
    exchange: str,
    limit: int = Query(default=50, ge=1, le=1000, description=""),
    db: AsyncSession = Depends(get_database_session),
) -> YieldResponse:
    try:
        exchange_lower = exchange.lower().strip()
        if exchange_lower not in [
            "binance",
            "bybit",
            "okx",
            "mexc",
            "bitmart",
            "gate",
            "bitget",
            "kraken",
            "kucoin",
            "htx",
        ]:
            raise HTTPException(
                status_code=400,
                detail=f"Непідтримувана біржа '{exchange}'. Доступні: binance, bybit, okx, mexc, bitmart, gate, bitget, kraken, kucoin, htx",
            )

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
            "htx": "HTX",
        }
        provider_db = provider_mapping.get(exchange_lower, exchange_lower.title())

        logger.info(
            f"🔥 Запит продуктів {exchange_lower} відсортованих за популярністю: limit={limit}"
        )

        logger.info(f"🔥 Отримуємо всі продукти {exchange_lower} відсортовані за популярністю")
        from app.db.crud import YieldProductCRUD

        products = await YieldProductCRUD.get_products_by_provider_with_popularity_sorting(
            db, provider_db, limit
        )
        logger.info(
            f"🔥 Отримано {len(products)} продуктів {exchange_lower} відсортованих за популярністю"
        )

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
                    product_type=getattr(product, "product_type", None),
                    category=getattr(product, "category", None),
                    is_active=product.is_active,
                    website_url=product.website_url,
                    description=product.description,
                    risk_level=product.risk_level,
                )
                yield_products.append(yield_product)
                converted_count += 1
            except Exception as conv_error:
                logger.warning(f"❌ Помилка конвертації продукту {product.id}: {conv_error}")
                continue

        logger.info(f"✅ Конвертовано {converted_count}/{len(products)} продуктів")
        logger.info(
            f"✅ Повертаємо {len(yield_products)} продуктів {exchange_lower} за популярністю"
        )

        return YieldResponse(
            success=True,
            data=yield_products,
            count=len(yield_products),
            message=f"Продукти {exchange_lower} відсортовані за популярністю монет",
            cached=False,
            source=f"database_{exchange_lower}_popularity_sorted",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"[API] Помилка отримання продуктів {exchange} за популярністю: {e}", exc_info=True
        )
        return YieldResponse(
            success=False,
            data=[],
            count=0,
            message=f"Помилка отримання продуктів {exchange}: {str(e)}",
            cached=False,
            source="error",
        )


# =============================================================================
# MEXC Manual Import Endpoints
# =============================================================================


@router.post("/mexc/import", response_model=dict, tags=["mexc"])
async def import_mexc_products(import_data: dict):
    try:
        from app.services.exchanges.mexc.models import MEXCManualImport

        validated_data = MEXCManualImport(**import_data)

        if validated_data.exchange.upper() != "MEXC":
            raise HTTPException(status_code=400, detail="exchange має бути 'MEXC'")

        created_count = 0
        updated_count = 0
        errors = []

        async with get_database_session() as db:
            for product in validated_data.products:
                try:
                    if product.lock_period_days == 0:
                        product_id = f"mexc_flexible_{product.symbol.lower()}"
                    else:
                        product_id = (
                            f"mexc_locked_{product.symbol.lower()}_{product.lock_period_days}"
                        )

                    product_data = YieldProductCreate(
                        id=product_id,
                        symbol=product.symbol.upper(),
                        name=f"{product.symbol.upper()} {product.product_type} Savings"
                        + (
                            f" ({product.lock_period_days} days)"
                            if product.lock_period_days > 0
                            else ""
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
                        raw_data=product.dict(),
                    )

                    existing = await YieldProductCRUD.get_product_by_id(db, product_id)
                    if existing:
                        await YieldProductCRUD.update_product(
                            db, product_id, product_data.dict(exclude_unset=True)
                        )
                        updated_count += 1
                    else:
                        await YieldProductCRUD.create_product(db, product_data)
                        created_count += 1

                except Exception as e:
                    errors.append(f"{product.symbol}: {str(e)}")
                    logger.error(f"Помилка імпорту продукту {product.symbol}: {e}")

            await db.commit()

        result = {
            "success": True,
            "created": created_count,
            "updated": updated_count,
            "total": len(validated_data.products),
            "errors": errors,
            "imported_at": datetime.now(UTC).isoformat(),
        }

        logger.info(f"MEXC імпорт завершено: {created_count} створено, {updated_count} оновлено")
        return result

    except Exception as e:
        logger.error(f"Помилка імпорту MEXC: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Помилка імпорту: {str(e)}")


@router.get("/mexc/test", response_model=dict, tags=["mexc"])
async def test_mexc_connection():
    from app.services.exchanges.mexc.service import MEXCService

    service = MEXCService()
    result = await service.test_connection()
    return result


@router.get("/mexc/products", response_model=YieldResponse, tags=["mexc"])
async def get_mexc_products(
    symbol: Optional[str] = Query(default=None, description=""),
    limit: Optional[int] = Query(default=100, description=""),
):
    from app.services.exchanges.mexc.service import MEXCService

    service = MEXCService()
    products = await service.get_products_with_cache(symbol=symbol)

    if limit:
        products = products[:limit]

    return create_success_response(products)


@router.post("/mexc/sync", response_model=dict, tags=["mexc"])
async def sync_mexc_products(symbol: Optional[str] = Query(default=None, description="")):
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
            "data": result,
        }
    except Exception as e:
        logger.error(f"❌ Помилка синхронізації MEXC: {e}")
        return {"success": False, "status": "error", "message": f"Помилка синхронізації: {str(e)}"}


# =============================================================================
# GATE.IO ENDPOINTS
# =============================================================================


@router.get("/gate/test", response_model=dict, tags=["gate"])
async def test_gate_connection():
    try:
        gate_service = exchange_registry.get_exchange_service("gate")
        result = await gate_service.test_connection()
        return {
            "success": True,
            "status": "success",
            "message": "Тест підключення до Gate.io API виконано",
            "data": result,
        }

    except Exception as e:
        logger.error(f"❌ Помилка тестування Gate.io API: {e}")
        return create_error_response(error="Помилка тестування Gate.io API", details=str(e))


@router.get("/gate/products", response_model=YieldResponse, tags=["gate"])
async def get_gate_products(
    symbol: Optional[str] = Query(None, description=""),
    limit: Optional[int] = Query(default=100, description=""),
):
    try:
        gate_service = exchange_registry.get_exchange_service("gate")
        products_data = await gate_service.get_products_with_cache(symbol)

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
            cached=True,
        )

    except Exception as e:
        logger.error(f"❌ Помилка отримання продуктів Gate.io: {e}")
        return create_error_response(error="Помилка отримання продуктів Gate.io", details=str(e))


@router.get("/exchanges/gate/products", response_model=YieldResponse, tags=["gate"])
async def get_gate_exchange_products(
    symbol: Optional[str] = Query(None, description=""),
    limit: Optional[int] = Query(default=100, description=""),
):
    return await get_gate_products(symbol=symbol, limit=limit)


@router.get("/exchanges/gate/popular", response_model=YieldResponse, tags=["gate"])
async def get_gate_popular(limit: Optional[int] = Query(default=10, description="")):
    try:
        gate_service = exchange_registry.get_exchange_service("gate")
        all_products = await gate_service.get_products_with_cache()

        yield_products = []
        for item in all_products:
            try:
                product = YieldProduct(**item)
                yield_products.append(product)
            except Exception as e:
                logger.warning(f"⚠️ Помилка конвертації продукту: {e}")

        sorted_products = sorted(yield_products, key=lambda p: p.apy, reverse=True)
        top_products = sorted_products[:limit]

        return create_success_response(
            data=top_products, message=f"Топ {len(top_products)} продуктів Gate.io за APY"
        )

    except Exception as e:
        logger.error(f"❌ Помилка отримання популярних Gate.io: {e}")
        return create_error_response(error="Помилка отримання популярних Gate.io", details=str(e))


@router.post("/gate/sync", response_model=dict, tags=["gate"])
async def sync_gate_products(symbol: Optional[str] = Query(None, description="")):
    try:
        gate_service = exchange_registry.get_exchange_service("gate")
        result = await gate_service.sync_products_to_db(symbol)

        if result["status"] == "success":
            return {
                "success": True,
                "status": "success",
                "message": f"Синхронізація Gate.io завершена: {result['sync_stats']['created']} створено, {result['sync_stats']['updated']} оновлено",
                "data": result,
            }
        else:
            return create_error_response(
                error=result.get("message", "Помилка синхронізації"), details=str(result)
            )

    except Exception as e:
        logger.error(f"❌ Помилка синхронізації Gate.io: {e}")
        return create_error_response(error="Помилка синхронізації Gate.io", details=str(e))


@router.post("/gate/import", response_model=dict, tags=["gate"])
async def import_gate_fixed_products(import_data: dict):
    try:
        if import_data.get("exchange", "").lower() != "gate":
            raise HTTPException(status_code=400, detail="exchange має бути 'gate'")

        products_list = import_data.get("products", [])
        if not products_list:
            raise HTTPException(status_code=400, detail="products не може бути порожнім")

        created_count = 0
        updated_count = 0
        errors = []

        async with get_database_session() as db:
            for product in products_list:
                try:
                    symbol = product.get("symbol", "").upper()
                    lock_days = product.get("lock_period_days", 0)
                    product_type = product.get("product_type", "Fixed")

                    if lock_days == 0:
                        product_id = f"gate_flexible_{symbol.lower()}"
                    else:
                        product_id = f"gate_fixed_{symbol.lower()}_{lock_days}"

                    product_data = YieldProductCreate(
                        id=product_id,
                        symbol=symbol,
                        name=f"{symbol} {product_type} Savings"
                        + (f" ({lock_days} days)" if lock_days > 0 else ""),
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
                        raw_data=product,
                    )

                    existing = await YieldProductCRUD.get_product_by_id(db, product_id)
                    if existing:
                        await YieldProductCRUD.update_product(
                            db, product_id, product_data.dict(exclude_unset=True)
                        )
                        updated_count += 1
                    else:
                        await YieldProductCRUD.create_product(db, product_data)
                        created_count += 1

                except Exception as e:
                    errors.append(f"{symbol}: {str(e)}")
                    logger.error(f"Помилка імпорту продукту {symbol}: {e}")

            await db.commit()

        result = {
            "success": True,
            "created": created_count,
            "updated": updated_count,
            "total": len(products_list),
            "errors": errors,
            "imported_at": datetime.now(UTC).isoformat(),
        }

        logger.info(f"Gate.io імпорт завершено: {created_count} створено, {updated_count} оновлено")
        return result

    except Exception as e:
        logger.error(f"Помилка імпорту Gate.io: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Помилка імпорту: {str(e)}")


@router.get("/gate/health", response_model=dict, tags=["gate"])
async def get_gate_health():
    try:
        gate_service = exchange_registry.get_exchange_service("gate")
        health_info = await gate_service.get_health_status()
        return {
            "success": True,
            "status": "success",
            "message": "Стан Gate.io сервісу перевірено",
            "data": health_info,
        }

    except Exception as e:
        logger.error(f"❌ Помилка перевірки Gate.io сервісу: {e}")
        return create_error_response(error="Помилка перевірки Gate.io сервісу", details=str(e))


# =============================================================================
# BITGET ENDPOINTS
# =============================================================================


@router.get("/bitget/test", response_model=dict, tags=["bitget"])
async def test_bitget_connection():
    try:
        from app.services.exchanges.bitget.service import BitgetService

        service = BitgetService()
        await service.initialize()
        result = await service.test_connection()
        return {
            "success": result.get("status") == "success",
            "status": result.get("status"),
            "message": result.get("message"),
            "data": result,
        }
    except Exception as e:
        logger.error(f"❌ Помилка тесту Bitget: {e}")
        return {
            "success": False,
            "status": "error",
            "message": f"Помилка тесту підключення: {str(e)}",
        }


@router.post("/bitget/sync", response_model=dict, tags=["bitget"])
async def sync_bitget_products():
    try:
        from app.services.exchanges.bitget.service import BitgetService

        service = BitgetService()
        await service.initialize()
        result = await service.sync_products_to_db()
        return {
            "success": result.get("status") == "success",
            "status": result.get("status"),
            "message": result.get("message"),
            "data": result,
        }
    except Exception as e:
        logger.error(f"❌ Помилка синхронізації Bitget: {e}")
        return {"success": False, "status": "error", "message": f"Помилка синхронізації: {str(e)}"}


@router.get("/bitget/health", response_model=dict, tags=["bitget"])
async def get_bitget_health():
    try:
        bitget_service = exchange_registry.get_exchange_service("bitget")
        health_info = await bitget_service.get_health_status()
        return {
            "success": True,
            "status": "success",
            "message": "Стан Bitget сервісу перевірено",
            "data": health_info,
        }
    except Exception as e:
        logger.error(f"❌ Помилка перевірки Bitget сервісу: {e}")
        return create_error_response(error="Помилка перевірки Bitget сервісу", details=str(e))


# =============================================================================
# Kraken endpoints
# =============================================================================


@router.get("/kraken/test")
async def test_kraken_connection():
    try:
        kraken_service = exchange_registry.get_exchange_service("kraken")
        result = await kraken_service.test_connection()
        return {
            "success": True,
            "status": "success",
            "message": "Тест підключення до Kraken API виконано",
            "data": result,
        }

    except Exception as e:
        logger.error(f"❌ Помилка тестування Kraken API: {e}")
        return create_error_response(error="Помилка тестування Kraken API", details=str(e))


@router.get("/kraken/products")
async def get_kraken_products(symbol: Optional[str] = Query(None, description="")):
    try:
        kraken_service = exchange_registry.get_exchange_service("kraken")
        products_data = await kraken_service.get_products_with_cache(symbol)

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
            cached=True,
        )

    except Exception as e:
        logger.error(f"❌ Помилка отримання продуктів Kraken: {e}")
        return create_error_response(error="Помилка отримання продуктів Kraken", details=str(e))


@router.post("/kraken/sync")
async def sync_kraken_products(symbol: Optional[str] = Query(None, description="")):
    try:
        kraken_service = exchange_registry.get_exchange_service("kraken")
        result = await kraken_service.sync_products_to_db(symbol)

        if result["status"] == "success":
            return {
                "success": True,
                "status": "success",
                "message": f"Синхронізація Kraken завершена: {result['sync_stats']['created']} створено, {result['sync_stats']['updated']} оновлено",
                "data": result,
            }
        else:
            return create_error_response(
                error=result.get("message", "Помилка синхронізації"), details=str(result)
            )

    except Exception as e:
        logger.error(f"❌ Помилка синхронізації Kraken продуктів: {e}")
        return create_error_response(error="Помилка синхронізації Kraken", details=str(e))


@router.get("/kraken/test-strategies")
async def test_kraken_strategies():
    try:
        kraken_service = exchange_registry.get_exchange_service("kraken")
        result = await kraken_service.api_client.test_different_strategies()
        return {
            "success": True,
            "status": "success",
            "message": "Тестування стратегій завершено",
            "data": [result],
            "timestamp": datetime.now(UTC).isoformat(),
        }
    except Exception as e:
        logger.error(f"❌ Помилка тестування стратегій Kraken: {e}")
        return create_error_response(error="Помилка тестування стратегій", details=str(e))


@router.get("/kraken/test-endpoints")
async def test_kraken_endpoints():
    try:
        kraken_service = exchange_registry.get_exchange_service("kraken")
        result = await kraken_service.api_client.test_other_endpoints()
        return {
            "success": True,
            "status": "success",
            "message": "Тестування ендпоінтів завершено",
            "data": [result],
            "timestamp": datetime.now(UTC).isoformat(),
        }
    except Exception as e:
        logger.error(f"❌ Помилка тестування ендпоінтів Kraken: {e}")
        return create_error_response(error="Помилка тестування ендпоінтів", details=str(e))


@router.get("/kraken/test-get-products")
async def test_kraken_get_products():
    try:
        kraken_service = exchange_registry.get_exchange_service("kraken")
        result = await kraken_service.api_client.get_earn_products()
        return {
            "success": True,
            "status": "success",
            "message": f"Отримано {len(result)} продуктів",
            "data": result,
            "timestamp": datetime.now(UTC).isoformat(),
        }
    except Exception as e:
        logger.error(f"❌ Помилка тестування get_earn_products Kraken: {e}")
        return create_error_response(error="Помилка тестування get_earn_products", details=str(e))


@router.post("/kraken/sync-direct")
async def sync_kraken_direct():
    try:
        kraken_service = exchange_registry.get_exchange_service("kraken")

        logger.info("🔄 Пряма синхронізація Kraken - отримуємо продукти з API...")
        products = await kraken_service.api_client.get_earn_products()
        logger.info(f"✅ Отримано {len(products)} продуктів з API")

        if not products:
            return create_error_response(
                error="Продукти не знайдено в API", details="API повернув порожній список продуктів"
            )

        normalized_products = await kraken_service._normalize_products(products)
        logger.info(f"✅ Нормалізовано {len(normalized_products)} продуктів")

        sync_stats = await kraken_service._save_products_to_db(normalized_products)
        logger.info(f"✅ Збережено в БД: {sync_stats}")

        return {
            "success": True,
            "status": "success",
            "message": f"Синхронізація завершена: {sync_stats['created']} створено, {sync_stats['updated']} оновлено",
            "data": {
                "api_products": len(products),
                "normalized_products": len(normalized_products),
                "sync_stats": sync_stats,
            },
            "timestamp": datetime.now(UTC).isoformat(),
        }

    except Exception as e:
        logger.error(f"❌ Помилка прямої синхронізації Kraken: {e}")
        return create_error_response(error="Помилка прямої синхронізації", details=str(e))


@router.get("/kraken/test-aggregation")
async def test_kraken_aggregation():
    try:
        from app.services.aggregation_service import aggregation_service

        data, sources, calls = await aggregation_service._get_exchange_data(
            "kraken", None, "kraken"
        )
        return {
            "success": True,
            "status": "success",
            "message": f"Агрегація повернула {len(data)} продуктів",
            "data": {
                "products_count": len(data),
                "sources": [s.value for s in sources],
                "api_calls": calls,
                "first_product": data[0] if data else None,
            },
            "timestamp": datetime.now(UTC).isoformat(),
        }
    except Exception as e:
        logger.error(f"❌ Помилка тестування агрегації Kraken: {e}")
        return create_error_response(error="Помилка тестування агрегації", details=str(e))


# =============================================================================
# PRIORITY PRODUCTS ENDPOINTS
# =============================================================================


@router.get("/priority-products/{exchange}")
async def get_priority_products(exchange: str = Path(..., description="")):
    try:
        exchange_lower = exchange.lower().strip()
        valid_exchanges = [
            "binance",
            "bybit",
            "okx",
            "mexc",
            "bitmart",
            "gate",
            "bitget",
            "kraken",
            "kucoin",
            "htx",
        ]

        if exchange_lower not in valid_exchanges:
            return create_error_response(
                error=f"Непідтримувана біржа '{exchange}'",
                details=f"Доступні: {', '.join(valid_exchanges)}",
            )

        from app.db.database import db_manager

        async with db_manager.get_session() as db:
            products = await PriorityProductCRUD.get_priority_products_by_exchange(
                db, exchange_lower
            )

        logger.info(f"📊 Отримано {len(products)} priority продуктів для {exchange_lower}")

        products_data = []
        for product in products:
            has_id = hasattr(product, "id") and product.id is not None
            logger.debug(
                f"  {product.symbol}: APY={product.apy}, is_active={product.is_active}, has_id={has_id}"
            )

            products_data.append(
                {
                    "symbol": product.symbol,
                    "apy": float(product.apy),
                    "is_active": product.is_active,
                    "product_id": product.product_id,
                    "lock_period_days": product.lock_period_days,
                    "exchange": product.exchange,
                    "updated_at": product.updated_at.isoformat() if product.updated_at else None,
                }
            )

        return {
            "success": True,
            "status": "success",
            "data": products_data,
            "count": len(products_data),
            "message": f"Отримано {len(products_data)} priority продуктів для {exchange_lower}",
            "cached": False,
            "source": "priority_products_table",
            "timestamp": datetime.now(UTC).isoformat(),
        }

    except Exception as e:
        logger.error(f"❌ Помилка отримання priority продуктів для {exchange}: {e}")
        return create_error_response(error="Помилка отримання priority продуктів", details=str(e))


@router.post("/priority-products/update")
async def update_priority_products(exchange: Optional[str] = Query(None, description="")):
    try:
        from app.services.priority_products_service import priority_products_service
        from app.db.database import db_manager

        async with db_manager.get_session() as db:
            if exchange:
                count = await priority_products_service.update_priority_products_for_exchange(
                    db, exchange.lower()
                )
                stats = {exchange.lower(): count, "total": count}
            else:
                stats = await priority_products_service.update_all_exchanges(db)

            logger.info(f"✅ Priority products оновлено: {stats}")

            return {
                "success": True,
                "status": "success",
                "message": f"Priority products оновлено: {stats.get('total', 0)} продуктів",
                "data": stats,
            }

    except Exception as e:
        logger.error(f"❌ Помилка оновлення priority_products: {e}", exc_info=True)
        return create_error_response(error="Помилка оновлення priority_products", details=str(e))


# =============================================================================
# TOP PRODUCTS ENDPOINT
# =============================================================================


@router.get("/top-products")
async def get_top_products_endpoint(limit: int = Query(10, ge=1, le=10, description="")):
    try:
        async with get_database_session() as db:
            result = await db.execute(select(TopProductDB).order_by(TopProductDB.rank).limit(limit))
            items = result.scalars().all()

        data = []
        for item in items:
            data.append(
                {
                    "rank": item.rank,
                    "symbol": item.symbol,
                    "coin_name": item.coin_name,
                    "market_cap_rank": item.market_cap_rank,
                    "best_apy": float(item.best_apy) if item.best_apy is not None else 0.0,
                    "best_exchange": item.best_exchange or None,
                    "product_id": item.product_id or None,
                    "updated_at": item.updated_at.isoformat() if item.updated_at else None,
                }
            )

        return {
            "success": True,
            "status": "success",
            "data": data,
            "count": len(data),
            "limit": limit,
            "source": "top_products_table",
            "timestamp": datetime.now(UTC).isoformat(),
        }

    except Exception as e:
        logger.error(f"❌ Помилка отримання top_products: {e}", exc_info=True)
        return create_error_response(error="Помилка отримання top_products", details=str(e))


# =============================================================================

# =============================================================================


__all__ = ["router", "metrics_router"]
