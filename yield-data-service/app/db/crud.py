from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func, and_, or_, desc, asc, insert
from sqlalchemy.orm import selectinload
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timedelta, UTC
import json

from app.db.models import (
    YieldProductDB,
    ExchangeDataDB,
    CacheMetadataDB,
    UserAnalyticsDB,
    SystemMetricsDB,
    APILogsDB,
    CoinsPopularityDB,
    PriorityProductDB,
    TopProductDB,
)
from app.db.database import get_database_session
from sqlalchemy import case
from app.models.yield_product import (
    YieldProduct,
    YieldProductCreate,
    YieldProductUpdate,
    YieldProductFilter,
)
from app.utils.logger import logger


# =============================================================================
# YIELD PRODUCTS CRUD OPERATIONS
# =============================================================================


class YieldProductCRUD:
    @staticmethod
    async def create_product(db: AsyncSession, product_data: YieldProductCreate) -> YieldProductDB:
        try:
            product_id = f"{product_data.provider.lower()}_{product_data.symbol.lower()}_{int(datetime.now(UTC).timestamp())}"

            db_product = YieldProductDB(
                id=product_id,
                symbol=product_data.symbol.upper(),
                name=product_data.name,
                provider=product_data.provider,
                apy=product_data.apy,
                is_cefi=product_data.is_cefi,
                min_amount=product_data.min_amount,
                max_amount=product_data.max_amount,
                lock_period_days=product_data.lock_period_days,
                max_apy=product_data.max_apy,
                risk_level=product_data.risk_level.value,
                is_active=product_data.is_active,
                website_url=product_data.website_url,
                description=product_data.description,
                raw_data=product_data.raw_data,
            )

            db.add(db_product)
            await db.commit()
            await db.refresh(db_product)

            logger.info(f"Створено новий продукт: {product_id}")
            return db_product

        except Exception as e:
            logger.error(f"Помилка створення продукту: {e}")
            await db.rollback()
            raise

    @staticmethod
    async def get_product_by_id(db: AsyncSession, product_id: str) -> Optional[YieldProductDB]:
        try:
            result = await db.execute(select(YieldProductDB).where(YieldProductDB.id == product_id))
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Помилка отримання продукту {product_id}: {e}")
            return None

    @staticmethod
    async def get_products_by_symbol(db: AsyncSession, symbol: str) -> List[YieldProductDB]:
        try:
            logger.info(
                f"🔍 Виконуємо запит до БД: SELECT * FROM yield_products WHERE symbol = '{symbol.upper()}' ORDER BY apy DESC"
            )
            result = await db.execute(
                select(YieldProductDB)
                .where(YieldProductDB.symbol == symbol.upper())
                .order_by(desc(YieldProductDB.apy))
            )
            products = result.scalars().all()
            logger.info(
                f"📊 БД повернула {len(products)} продуктів для {symbol}: {[f'{p.provider}:{p.name}' for p in products[:3]]}"
            )
            return products
        except Exception as e:
            logger.error(f"Помилка отримання продуктів по символу {symbol}: {e}")
            return []

    @staticmethod
    async def get_products_by_provider(db: AsyncSession, provider: str) -> List[YieldProductDB]:
        try:
            result = await db.execute(
                select(YieldProductDB)
                .where(YieldProductDB.provider == provider)
                .where(YieldProductDB.is_active == True)
                .order_by(desc(YieldProductDB.apy))
            )
            return result.scalars().all()
        except Exception as e:
            logger.error(f"Помилка отримання продуктів по провайдеру {provider}: {e}")
            return []

    @staticmethod
    async def get_products_by_symbol_and_provider(
        db: AsyncSession, symbol: str, provider: str
    ) -> List[YieldProductDB]:
        try:
            result = await db.execute(
                select(YieldProductDB)
                .where(YieldProductDB.symbol == symbol.upper())
                .where(YieldProductDB.provider == provider)
                .order_by(desc(YieldProductDB.apy))
            )
            products = result.scalars().all()
            logger.debug(
                f"🔍 get_products_by_symbol_and_provider({symbol}, {provider}): "
                f"знайдено {len(products)} продуктів"
            )
            return products
        except Exception as e:
            logger.error(f"Помилка отримання продуктів {symbol}/{provider}: {e}", exc_info=True)
            return []

    @staticmethod
    async def get_all_products(limit: Optional[int] = 100, offset: int = 0) -> List[YieldProductDB]:
        async with get_database_session() as db:
            try:
                logger.info(f"🔍 Отримання продуктів з БД: limit={limit}, offset={offset}")

                query = select(YieldProductDB).where(YieldProductDB.is_active == True)
                if limit is not None:
                    query = query.limit(limit).offset(offset)
                else:
                    query = query.offset(offset)

                result = await db.execute(query)
                products = result.scalars().all()

                logger.info(
                    f"✅ Знайдено {len(products)} активних продуктів в БД (limit={limit}, offset={offset})"
                )
                return products
            except Exception as e:
                logger.error(f"Помилка отримання всіх продуктів: {e}")
                return []

    @staticmethod
    async def get_all_products_sorted_by_popularity(
        limit: Optional[int] = None, offset: int = 0, filters: Optional[YieldProductFilter] = None
    ) -> List[YieldProductDB]:
        async with get_database_session() as db:
            try:
                logger.info(
                    f"🔍 Отримання продуктів з сортуванням за популярністю: limit={limit}, offset={offset}"
                )

                query = (
                    select(YieldProductDB)
                    .outerjoin(
                        CoinsPopularityDB,
                        func.upper(YieldProductDB.symbol) == func.upper(CoinsPopularityDB.symbol),
                    )
                    .where(YieldProductDB.is_active == True)
                )

                if filters:
                    if filters.symbol:
                        query = query.where(
                            func.upper(YieldProductDB.symbol) == filters.symbol.upper()
                        )
                    if filters.provider:
                        query = query.where(YieldProductDB.provider == filters.provider)
                    if filters.min_apy is not None:
                        query = query.where(YieldProductDB.apy >= filters.min_apy)
                    if filters.max_apy is not None:
                        query = query.where(YieldProductDB.apy <= filters.max_apy)
                    if filters.lock_period_days is not None:
                        query = query.where(
                            YieldProductDB.lock_period_days == filters.lock_period_days
                        )

                query = query.order_by(
                    func.coalesce(CoinsPopularityDB.market_cap_rank, 9999).asc(),
                    YieldProductDB.apy.desc(),
                )

                if limit is not None:
                    query = query.limit(limit)
                if offset > 0:
                    query = query.offset(offset)

                result = await db.execute(query)
                products = result.scalars().all()

                seen = set()
                unique_products = []
                for product in products:
                    if product.id not in seen:
                        seen.add(product.id)
                        unique_products.append(product)

                unique_products.sort(key=lambda p: p.id)

                logger.info(
                    f"✅ Отримано {len(unique_products)} продуктів з сортуванням за популярністю (було {len(products)} до видалення дублікатів)"
                )
                if unique_products:
                    logger.info(
                        f"🔍 Перші 5 продуктів: {[(p.symbol, p.provider, p.apy) for p in unique_products[:5]]}"
                    )

                return unique_products

            except Exception as e:
                logger.error(f"Помилка отримання продуктів за популярністю: {e}", exc_info=True)
                return []

    @staticmethod
    async def get_top_products(db: AsyncSession, limit: int = 20) -> List[YieldProductDB]:
        try:
            result = await db.execute(
                select(YieldProductDB)
                .where(YieldProductDB.is_active == True)
                .order_by(desc(YieldProductDB.apy))
                .limit(limit)
            )
            return result.scalars().all()
        except Exception as e:
            logger.error(f"Помилка отримання топ продуктів: {e}")
            return []

    async def get_top_products_by_provider(
        db: AsyncSession, limit_per_provider: int = 10
    ) -> Dict[str, List[YieldProductDB]]:
        try:
            providers_result = await db.execute(
                select(YieldProductDB.provider.distinct()).where(YieldProductDB.is_active == True)
            )
            providers = [row[0] for row in providers_result.all()]

            result = {}
            for provider in providers:
                provider_products = await db.execute(
                    select(YieldProductDB)
                    .where(YieldProductDB.is_active == True)
                    .where(YieldProductDB.provider == provider)
                    .order_by(desc(YieldProductDB.apy))
                    .limit(limit_per_provider)
                )
                products = provider_products.scalars().all()
                if products:
                    result[provider] = products

            logger.info(f"📊 Отримано топ продукти по {len(result)} біржам: {list(result.keys())}")
            return result
        except Exception as e:
            logger.error(f"Помилка отримання топ продуктів по provider'ам: {e}")
            return {}

    @staticmethod
    async def get_products_sorted_by_popularity(
        db: AsyncSession, limit: int = 100, offset: int = 0
    ) -> List[YieldProductDB]:
        try:
            logger.info("🔍 Починаємо створення запиту сортування за популярністю")

            query = (
                select(YieldProductDB)
                .outerjoin(
                    CoinsPopularityDB,
                    func.upper(YieldProductDB.symbol) == func.upper(CoinsPopularityDB.symbol),
                )
                .where(YieldProductDB.is_active == True)
                .order_by(
                    func.coalesce(CoinsPopularityDB.market_cap_rank, 9999).asc(),
                    desc(YieldProductDB.apy),
                )
                .limit(limit)
                .offset(offset)
            )

            logger.info(f"🔍 Запит створено: LIMIT {limit}, OFFSET {offset}")
            logger.info("🔍 Виконуємо SQL запит до БД...")
            result = await db.execute(query)
            products = result.scalars().all()
            logger.info(f"🔍 SQL запит виконано, отримано {len(products)} продуктів")

            logger.info(f"✅ Отримано {len(products)} продуктів відсортованих за популярністю")
            return products

        except Exception as e:
            logger.error(
                f"❌ Помилка отримання продуктів відсортованих за популярністю: {e}", exc_info=True
            )
            return []

    @staticmethod
    async def get_products_by_provider_sorted_by_popularity(
        db: AsyncSession, provider: str, limit: int = 50
    ) -> List[YieldProductDB]:
        try:
            query = (
                select(YieldProductDB)
                .outerjoin(
                    CoinsPopularityDB,
                    func.upper(YieldProductDB.symbol) == func.upper(CoinsPopularityDB.symbol),
                )
                .where(YieldProductDB.is_active == True)
                .where(YieldProductDB.provider == provider)
                .order_by(
                    func.coalesce(CoinsPopularityDB.market_cap_rank, 9999).asc(),
                    desc(YieldProductDB.apy),
                )
                .limit(limit)
            )

            logger.info(f"🔍 Отримуємо продукти {provider} відсортовані за популярністю")
            logger.info("🔍 Виконуємо SQL запит до БД...")

            count_query = (
                select(func.count())
                .select_from(YieldProductDB)
                .where(YieldProductDB.is_active == True)
                .where(YieldProductDB.provider == provider)
            )
            total_count = await db.execute(count_query)
            total_products = total_count.scalar()
            logger.warning(f"🔍 Загальна кількість продуктів {provider}: {total_products}")

            result = await db.execute(query)
            products = result.scalars().all()
            logger.warning(
                f"🔍 SQL запит виконано, отримано {len(products)} продуктів після JOIN з популярністю"
            )

            logger.info(f"✅ Отримано {len(products)} продуктів {provider} за популярністю")
            return products

        except Exception as e:
            logger.error(f"Помилка отримання продуктів {provider} за популярністю: {e}")
            return []

    @staticmethod
    async def get_products_by_provider_with_popularity_sorting(
        session, provider: str, limit: int = 50
    ) -> List[YieldProductDB]:
        try:
            if hasattr(session, "__aenter__"):
                async with session as db:
                    return await YieldProductCRUD._get_products_sorted_by_popularity_internal(
                        db, provider, limit
                    )
            else:
                return await YieldProductCRUD._get_products_sorted_by_popularity_internal(
                    session, provider, limit
                )

        except Exception as e:
            logger.error(
                f"❌ Помилка отримання продуктів {provider} з сортуванням за популярністю: {e}",
                exc_info=True,
            )

            try:
                if hasattr(session, "__aenter__"):
                    async with session as db:
                        result = await db.execute(
                            select(YieldProductDB)
                            .where(YieldProductDB.is_active == True)
                            .where(YieldProductDB.provider == provider)
                            .order_by(desc(YieldProductDB.apy))
                            .limit(limit)
                        )
                        return result.scalars().all()
                else:
                    result = await session.execute(
                        select(YieldProductDB)
                        .where(YieldProductDB.is_active == True)
                        .where(YieldProductDB.provider == provider)
                        .order_by(desc(YieldProductDB.apy))
                        .limit(limit)
                    )
                    return result.scalars().all()
            except Exception as fallback_error:
                logger.error(f"❌ Помилка fallback для {provider}: {fallback_error}")
                return []

    @staticmethod
    async def _get_products_sorted_by_popularity_internal(
        db: AsyncSession, provider: str, limit: int
    ) -> List[YieldProductDB]:

        result = await db.execute(
            select(YieldProductDB)
            .where(YieldProductDB.is_active == True)
            .where(YieldProductDB.provider == provider)
        )
        products = result.scalars().all()
        logger.info(
            f"🔍 Отримано {len(products)} продуктів {provider} для сортування за популярністю"
        )

        if not products:
            return []

        popularity_result = await db.execute(select(CoinsPopularityDB))
        popularity_data = {
            p.symbol.upper(): p.market_cap_rank for p in popularity_result.scalars().all()
        }
        logger.info(f"📊 Отримано дані про популярність для {len(popularity_data)} монет")

        def sort_key(product):
            symbol_upper = product.symbol.upper()
            popularity_rank = popularity_data.get(symbol_upper, 9999)
            return (popularity_rank, -product.apy, product.id)

        products.sort(key=sort_key)
        logger.info(f"🐍 Відсортовано {len(products)} продуктів {provider} за популярністю")

        products = products[:limit]
        logger.info(f"📊 Повертаємо {len(products)} продуктів {provider} після обмеження")

        return products

    @staticmethod
    async def get_all_coins_popularity() -> List[CoinsPopularityDB]:
        async with get_database_session() as db:
            try:
                result = await db.execute(select(CoinsPopularityDB))
                return result.scalars().all()
            except Exception as e:
                logger.error(f"Помилка отримання всіх записів популярності монет: {e}")
            return []

    @staticmethod
    async def filter_products(
        filters: YieldProductFilter, limit: Optional[int] = None
    ) -> List[YieldProductDB]:
        async with get_database_session() as db:
            try:
                query = select(YieldProductDB).where(YieldProductDB.is_active == True)

                if filters.symbol:
                    query = query.where(YieldProductDB.symbol == filters.symbol.upper())
                if filters.provider:
                    query = query.where(YieldProductDB.provider == filters.provider)
                if filters.min_apy is not None:
                    query = query.where(YieldProductDB.apy >= filters.min_apy)
                if filters.max_apy is not None:
                    query = query.where(YieldProductDB.apy <= filters.max_apy)
                if filters.is_cefi is not None:
                    query = query.where(YieldProductDB.is_cefi == filters.is_cefi)
                if filters.risk_level:
                    query = query.where(YieldProductDB.risk_level == filters.risk_level.value)
                if filters.min_amount is not None:
                    query = query.where(YieldProductDB.min_amount >= filters.min_amount)
                if filters.max_amount is not None:
                    query = query.where(YieldProductDB.max_amount <= filters.max_amount)
                if filters.lock_period_days is not None:
                    query = query.where(YieldProductDB.lock_period_days == filters.lock_period_days)

                query = query.order_by(desc(YieldProductDB.apy))

                if limit is not None:
                    query = query.limit(limit)

                result = await db.execute(query)
                return result.scalars().all()
            except Exception as e:
                logger.error(f"Помилка фільтрації продуктів: {e}")
                return []

    @staticmethod
    async def update_product(
        db: AsyncSession, product_id: str, update_data: YieldProductUpdate
    ) -> Optional[YieldProductDB]:
        try:
            product = await YieldProductCRUD.get_product_by_id(db, product_id)
            if not product:
                return None

            try:
                update_dict = update_data.model_dump(exclude_unset=True)
            except AttributeError:
                # Backward-compatible fallback
                update_dict = update_data.dict(exclude_unset=True)
            if update_dict:
                update_dict["updated_at"] = datetime.now(UTC).replace(tzinfo=None)

                await db.execute(
                    update(YieldProductDB)
                    .where(YieldProductDB.id == product_id)
                    .values(**update_dict)
                )
                await db.commit()
                await db.refresh(product)

                return await YieldProductCRUD.get_product_by_id(db, product_id)

            return product
        except Exception as e:
            logger.error(f"Помилка оновлення продукту {product_id}: {e}")
            await db.rollback()
            return None

    @staticmethod
    async def delete_product(db: AsyncSession, product_id: str) -> bool:
        try:
            await db.execute(delete(YieldProductDB).where(YieldProductDB.id == product_id))
            await db.commit()
            logger.info(f"Видалено продукт: {product_id}")
            return True
        except Exception as e:
            logger.error(f"Помилка видалення продукту {product_id}: {e}")
            await db.rollback()
            return False

    @staticmethod
    async def bulk_create_products(
        db: AsyncSession, products_data: List[YieldProductCreate]
    ) -> List[YieldProductDB]:
        try:
            created_products = []
            for product_data in products_data:
                product_id = f"{product_data.provider.lower()}_{product_data.symbol.lower()}_{int(datetime.now(UTC).timestamp())}"

                db_product = YieldProductDB(
                    id=product_id,
                    symbol=product_data.symbol.upper(),
                    name=product_data.name,
                    provider=product_data.provider,
                    apy=product_data.apy,
                    is_cefi=product_data.is_cefi,
                    min_amount=product_data.min_amount,
                    max_amount=product_data.max_amount,
                    lock_period_days=product_data.lock_period_days,
                    max_apy=product_data.max_apy,
                    risk_level=product_data.risk_level.value,
                    is_active=product_data.is_active,
                    website_url=product_data.website_url,
                    description=product_data.description,
                    raw_data=product_data.raw_data,
                )
                created_products.append(db_product)
                db.add(db_product)

            await db.commit()

            for product in created_products:
                await db.refresh(product)

            logger.info(f"Масово створено {len(created_products)} продуктів")
            return created_products

        except Exception as e:
            logger.error(f"Помилка масового створення продуктів: {e}")
            await db.rollback()
            return []

    @staticmethod
    async def get_products_count(db: AsyncSession, active_only: bool = True) -> int:
        try:
            query = select(func.count(YieldProductDB.id))
            if active_only:
                query = query.where(YieldProductDB.is_active == True)

            result = await db.execute(query)
            return result.scalar() or 0
        except Exception as e:
            logger.error(f"Помилка підрахунку продуктів: {e}")
            return 0


# =============================================================================
# EXCHANGE DATA CRUD OPERATIONS
# =============================================================================


class ExchangeDataCRUD:
    @staticmethod
    async def create_exchange_data(
        db: AsyncSession,
        product_id: str,
        exchange: str,
        raw_data: Dict[str, Any],
        api_endpoint: str = None,
        response_status: int = None,
        response_time_ms: int = None,
        request_timestamp: Optional[datetime] = None,
    ) -> ExchangeDataDB:
        try:
            db_exchange_data = ExchangeDataDB(
                product_id=product_id,
                exchange=exchange,
                raw_data=raw_data,
                api_endpoint=api_endpoint,
                response_status=response_status,
                response_time_ms=response_time_ms,
            )

            if request_timestamp:
                if request_timestamp.tzinfo is not None:
                    db_exchange_data.request_timestamp = request_timestamp.replace(tzinfo=None)
                else:
                    db_exchange_data.request_timestamp = request_timestamp

            db.add(db_exchange_data)
            await db.commit()
            await db.refresh(db_exchange_data)

            logger.info(f"Створено дані з біржі {exchange} для продукту {product_id}")
            return db_exchange_data

        except Exception as e:
            logger.error(f"Помилка створення даних з біржі: {e}")
            await db.rollback()
            raise

    @staticmethod
    async def get_exchange_data_by_product(
        db: AsyncSession, product_id: str
    ) -> List[ExchangeDataDB]:
        try:
            result = await db.execute(
                select(ExchangeDataDB)
                .where(ExchangeDataDB.product_id == product_id)
                .order_by(desc(ExchangeDataDB.request_timestamp))
            )
            return result.scalars().all()
        except Exception as e:
            logger.error(f"Помилка отримання даних з бірж для продукту {product_id}: {e}")
            return []

    @staticmethod
    async def get_exchange_data_by_exchange(
        db: AsyncSession, exchange: str
    ) -> List[ExchangeDataDB]:
        try:
            result = await db.execute(
                select(ExchangeDataDB)
                .where(ExchangeDataDB.exchange == exchange)
                .order_by(desc(ExchangeDataDB.request_timestamp))
            )
            return result.scalars().all()
        except Exception as e:
            logger.error(f"Помилка отримання даних з біржі {exchange}: {e}")
            return []

    @staticmethod
    async def get_latest_exchange_data(
        db: AsyncSession, exchange: str, limit: int = 100
    ) -> List[ExchangeDataDB]:
        try:
            result = await db.execute(
                select(ExchangeDataDB)
                .where(ExchangeDataDB.exchange == exchange)
                .order_by(desc(ExchangeDataDB.request_timestamp))
                .limit(limit)
            )
            return result.scalars().all()
        except Exception as e:
            logger.error(f"Помилка отримання останніх даних з біржі {exchange}: {e}")
            return []


# =============================================================================
# CACHE METADATA CRUD OPERATIONS
# =============================================================================


class CacheMetadataCRUD:
    @staticmethod
    async def create_cache_metadata(
        db: AsyncSession,
        cache_key: str,
        cache_type: str,
        expires_at: datetime,
        data_size_bytes: int = None,
    ) -> CacheMetadataDB:
        try:
            db_cache_metadata = CacheMetadataDB(
                cache_key=cache_key,
                cache_type=cache_type,
                expires_at=expires_at,
                data_size_bytes=data_size_bytes,
            )

            db.add(db_cache_metadata)
            await db.commit()
            await db.refresh(db_cache_metadata)

            logger.info(f"Створено метадані кешу: {cache_key}")
            return db_cache_metadata

        except Exception as e:
            logger.error(f"Помилка створення метаданих кешу: {e}")
            await db.rollback()
            raise

    @staticmethod
    async def get_cache_metadata(db: AsyncSession, cache_key: str) -> Optional[CacheMetadataDB]:
        try:
            result = await db.execute(
                select(CacheMetadataDB).where(CacheMetadataDB.cache_key == cache_key)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Помилка отримання метаданих кешу {cache_key}: {e}")
            return None

    @staticmethod
    async def update_cache_access(db: AsyncSession, cache_key: str, is_hit: bool = True) -> bool:
        try:
            metadata = await CacheMetadataCRUD.get_cache_metadata(db, cache_key)
            if not metadata:
                return False

            if is_hit:
                metadata.hit_count += 1
            else:
                metadata.miss_count += 1

            metadata.access_count += 1
            metadata.last_accessed = datetime.now(UTC).replace(tzinfo=None)

            await db.commit()
            return True

        except Exception as e:
            logger.error(f"Помилка оновлення статистики кешу {cache_key}: {e}")
            await db.rollback()
            return False

    @staticmethod
    async def get_expired_cache_keys(db: AsyncSession) -> List[str]:
        try:
            result = await db.execute(
                select(CacheMetadataDB.cache_key).where(
                    CacheMetadataDB.expires_at < datetime.now(UTC).replace(tzinfo=None)
                )
            )
            return [row[0] for row in result.fetchall()]
        except Exception as e:
            logger.error(f"Помилка отримання закінчених ключів кешу: {e}")
            return []

    @staticmethod
    async def delete_expired_cache(db: AsyncSession) -> int:
        try:
            result = await db.execute(
                delete(CacheMetadataDB).where(
                    CacheMetadataDB.expires_at < datetime.now(UTC).replace(tzinfo=None)
                )
            )
            await db.commit()

            deleted_count = result.rowcount
            logger.info(f"Видалено {deleted_count} закінчених записів кешу")
            return deleted_count

        except Exception as e:
            logger.error(f"Помилка видалення закінчених записів кешу: {e}")
            await db.rollback()
            return 0

    @staticmethod
    async def get_cache_statistics(db: AsyncSession) -> Dict[str, Any]:
        try:
            total_result = await db.execute(select(func.count(CacheMetadataDB.id)))
            total_count = total_result.scalar() or 0

            type_result = await db.execute(
                select(
                    CacheMetadataDB.cache_type, func.count(CacheMetadataDB.id).label("count")
                ).group_by(CacheMetadataDB.cache_type)
            )
            type_stats = {row[0]: row[1] for row in type_result.fetchall()}

            hit_result = await db.execute(
                select(
                    func.sum(CacheMetadataDB.hit_count).label("total_hits"),
                    func.sum(CacheMetadataDB.miss_count).label("total_misses"),
                )
            )
            hit_row = hit_result.fetchone()
            total_hits = hit_row[0] or 0
            total_misses = hit_row[1] or 0
            total_requests = total_hits + total_misses
            hit_rate = (total_hits / total_requests * 100) if total_requests > 0 else 0

            return {
                "total_cache_entries": total_count,
                "cache_types": type_stats,
                "total_hits": total_hits,
                "total_misses": total_misses,
                "total_requests": total_requests,
                "hit_rate_percent": round(hit_rate, 2),
            }

        except Exception as e:
            logger.error(f"Помилка отримання статистики кешу: {e}")
            return {}


# =============================================================================
# BULK OPERATIONS
# =============================================================================


class BulkOperations:
    @staticmethod
    async def bulk_upsert_products(
        db: AsyncSession, products_data: List[Dict[str, Any]]
    ) -> Tuple[int, int]:
        try:
            updated_count = 0
            created_count = 0

            for product_data in products_data:
                existing_product = await YieldProductCRUD.get_product_by_id(db, product_data["id"])

                if existing_product:
                    update_data = YieldProductUpdate(**product_data)
                    await YieldProductCRUD.update_product(db, product_data["id"], update_data)
                    updated_count += 1
                else:
                    create_data = YieldProductCreate(**product_data)
                    await YieldProductCRUD.create_product(db, create_data)
                    created_count += 1

            await db.commit()
            logger.info(f"Масове оновлення: {updated_count} оновлено, {created_count} створено")
            return updated_count, created_count

        except Exception as e:
            logger.error(f"Помилка масового оновлення продуктів: {e}")
            await db.rollback()
            return 0, 0

    @staticmethod
    async def bulk_create_exchange_data(
        db: AsyncSession, exchange_data_list: List[Dict[str, Any]]
    ) -> int:
        try:
            created_count = 0

            for data in exchange_data_list:
                await ExchangeDataCRUD.create_exchange_data(
                    db=db,
                    product_id=data["product_id"],
                    exchange=data["exchange"],
                    raw_data=data["raw_data"],
                    api_endpoint=data.get("api_endpoint"),
                    response_status=data.get("response_status"),
                    response_time_ms=data.get("response_time_ms"),
                )
                created_count += 1

            await db.commit()
            logger.info(f"Масово створено {created_count} записів даних з бірж")
            return created_count

        except Exception as e:
            logger.error(f"Помилка масового створення даних з бірж: {e}")
            await db.rollback()
            return 0

    @staticmethod
    async def cleanup_old_data(db: AsyncSession, days_old: int = 30) -> Dict[str, int]:
        try:
            cutoff_date = datetime.now(UTC).replace(tzinfo=None) - timedelta(days=days_old)
            deleted_counts = {}

            exchange_result = await db.execute(
                delete(ExchangeDataDB).where(ExchangeDataDB.request_timestamp < cutoff_date)
            )
            deleted_counts["exchange_data"] = exchange_result.rowcount

            cache_result = await db.execute(
                delete(CacheMetadataDB).where(CacheMetadataDB.expires_at < cutoff_date)
            )
            deleted_counts["cache_metadata"] = cache_result.rowcount

            await db.commit()
            logger.info(f"Очищено старі дані: {deleted_counts}")
            return deleted_counts

        except Exception as e:
            logger.error(f"Помилка очищення старих даних: {e}")
            await db.rollback()
            return {}


# =============================================================================
# COINS POPULARITY CRUD OPERATIONS
# =============================================================================


class CoinsPopularityCRUD:
    @staticmethod
    async def create_or_update_coins_popularity(
        db: AsyncSession, popularity_data: Dict[str, Any]
    ) -> CoinsPopularityDB:
        try:
            existing_record = await db.execute(
                select(CoinsPopularityDB).where(
                    or_(
                        CoinsPopularityDB.coin_id == popularity_data["coin_id"],
                        CoinsPopularityDB.symbol == popularity_data["symbol"],
                    )
                )
            )
            existing = existing_record.scalar_one_or_none()

            if existing:
                for key, value in popularity_data.items():
                    if hasattr(existing, key):
                        setattr(existing, key, value)
                logger.debug(f"Оновлено популярність для {popularity_data['symbol']}")
                return existing
            else:
                db_record = CoinsPopularityDB(**popularity_data)
                db.add(db_record)
                logger.debug(f"Створено новий запис популярності для {popularity_data['symbol']}")
                return db_record

        except Exception as e:
            logger.error(
                f"Помилка створення/оновлення популярності для {popularity_data.get('symbol', '?')}: {e}"
            )
            raise

    @staticmethod
    async def get_popularity_by_symbol(
        db: AsyncSession, symbol: str
    ) -> Optional[CoinsPopularityDB]:
        try:
            normalized_symbol = symbol.upper()

            result = await db.execute(
                select(CoinsPopularityDB).where(CoinsPopularityDB.symbol == normalized_symbol)
            )
            return result.scalar_one_or_none()

        except Exception as e:
            logger.error(f"Помилка отримання популярності для {symbol}: {e}")
            return None

    @staticmethod
    async def get_popularity_rank(db: AsyncSession, symbol: str) -> Optional[int]:
        record = await CoinsPopularityCRUD.get_popularity_by_symbol(db, symbol)
        return record.market_cap_rank if record else None

    @staticmethod
    async def get_top_popular_coins(db: AsyncSession, limit: int = 10) -> List[CoinsPopularityDB]:
        try:
            result = await db.execute(
                select(CoinsPopularityDB)
                .order_by(asc(CoinsPopularityDB.market_cap_rank))
                .limit(limit)
            )
            return result.scalars().all()

        except Exception as e:
            logger.error(f"Помилка отримання топ популярних монет: {e}")
            return []

    @staticmethod
    async def get_popularity_stats(db: AsyncSession) -> Dict[str, Any]:
        try:
            total_result = await db.execute(select(func.count(CoinsPopularityDB.id)))
            total_coins = total_result.scalar() or 0

            last_update_result = await db.execute(select(func.max(CoinsPopularityDB.updated_at)))
            last_update = last_update_result.scalar()

            top_result = await db.execute(
                select(CoinsPopularityDB.symbol, CoinsPopularityDB.market_cap_rank)
                .order_by(asc(CoinsPopularityDB.market_cap_rank))
                .limit(5)
            )
            top_coins = top_result.all()

            return {
                "total_coins": total_coins,
                "last_update": last_update.isoformat() if last_update else None,
                "top_coins": [{"symbol": coin[0], "rank": coin[1]} for coin in top_coins],
            }

        except Exception as e:
            logger.error(f"Помилка отримання статистики популярності: {e}")
            return {"total_coins": 0, "last_update": None, "top_coins": []}

    @staticmethod
    async def clear_old_popularity_data(db: AsyncSession, days_to_keep: int = 30) -> int:
        try:
            cutoff_date = datetime.now(UTC).replace(tzinfo=None) - timedelta(days=days_to_keep)

            result = await db.execute(
                delete(CoinsPopularityDB).where(CoinsPopularityDB.updated_at < cutoff_date)
            )

            deleted_count = result.rowcount
            logger.info(f"Видалено {deleted_count} старих записів популярності")

            return deleted_count

        except Exception as e:
            logger.error(f"Помилка очищення старих даних популярності: {e}")
            return 0


class TopProductCRUD:
    @staticmethod
    async def upsert_top_product(
        db: AsyncSession,
        rank: int,
        symbol: str,
        coin_name: Optional[str],
        market_cap_rank: Optional[int],
        best_apy: float,
        best_exchange: Optional[str],
        product_id: Optional[str],
    ) -> TopProductDB:
        now = datetime.now(UTC).replace(tzinfo=None)
        stmt = (
            insert(TopProductDB)
            .values(
                rank=rank,
                symbol=symbol,
                coin_name=coin_name,
                market_cap_rank=market_cap_rank,
                best_apy=best_apy,
                best_exchange=best_exchange,
                product_id=product_id,
                created_at=now,
                updated_at=now,
            )
            .on_conflict_do_update(
                index_elements=[TopProductDB.rank],
                set_=dict(
                    symbol=symbol,
                    coin_name=coin_name,
                    market_cap_rank=market_cap_rank,
                    best_apy=best_apy,
                    best_exchange=best_exchange,
                    product_id=product_id,
                    updated_at=now,
                ),
            )
            .returning(TopProductDB)
        )
        result = await db.execute(stmt)
        await db.commit()
        return result.scalar_one()

    @staticmethod
    async def get_top_products(db: AsyncSession, limit: int = 10) -> List[TopProductDB]:
        result = await db.execute(select(TopProductDB).order_by(TopProductDB.rank).limit(limit))
        return result.scalars().all()

    @staticmethod
    async def get_best_flexible_product(db: AsyncSession, symbol: str) -> Optional[YieldProductDB]:
        result = await db.execute(
            select(YieldProductDB)
            .where(YieldProductDB.symbol == symbol.upper())
            .where(YieldProductDB.is_active == True)
            .where(YieldProductDB.lock_period_days == 0)
            .order_by(desc(YieldProductDB.apy))
            .limit(1)
        )
        return result.scalar_one_or_none()


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================


async def create_or_update_coins_popularity(
    db: AsyncSession, popularity_data: Dict[str, Any]
) -> CoinsPopularityDB:
    return await CoinsPopularityCRUD.create_or_update_coins_popularity(db, popularity_data)


async def get_products_sorted_by_popularity(
    limit: int = 100, offset: int = 0
) -> List[YieldProductDB]:
    async with get_database_session() as session:
        return await YieldProductCRUD.get_products_sorted_by_popularity(
            session, limit=limit, offset=offset
        )


async def get_products_by_provider_sorted_by_popularity(
    session: AsyncSession, provider: str, limit: int = 50
) -> List[YieldProductDB]:
    return await YieldProductCRUD.get_products_by_provider_sorted_by_popularity(
        session, provider=provider, limit=limit
    )


async def get_database_stats(db: AsyncSession) -> Dict[str, Any]:
    try:
        stats = {}

        active_products_count = await YieldProductCRUD.get_products_count(db, active_only=True)
        stats["total_products"] = active_products_count

        cache_stats = await CacheMetadataCRUD.get_cache_statistics(db)
        stats.update(cache_stats)

        exchange_result = await db.execute(select(func.count(ExchangeDataDB.id)))
        stats["total_exchange_data"] = exchange_result.scalar() or 0

        return stats

    except Exception as e:
        logger.error(f"Помилка отримання статистики БД: {e}")
        return {}


# =============================================================================
# PRIORITY PRODUCTS CRUD OPERATIONS
# =============================================================================


class PriorityProductCRUD:
    SYMBOL_ORDER = ["BTC", "ETH", "SOL", "USDT"]

    @staticmethod
    async def get_priority_products_by_exchange(
        db: AsyncSession, exchange: str
    ) -> List[PriorityProductDB]:
        try:
            result = await db.execute(
                select(PriorityProductDB).where(PriorityProductDB.exchange == exchange.lower())
            )
            products = result.scalars().all()

            products_dict = {p.symbol: p for p in products}

            ordered_products = []
            for symbol in PriorityProductCRUD.SYMBOL_ORDER:
                if symbol in products_dict:
                    ordered_products.append(products_dict[symbol])
                else:
                    ordered_products.append(
                        PriorityProductDB(
                            exchange=exchange.lower(),
                            symbol=symbol,
                            apy=0.0,
                            is_active=False,
                            product_id=None,
                            lock_period_days=0,
                        )
                    )

            return ordered_products

        except Exception as e:
            logger.error(f"Помилка отримання priority продуктів для {exchange}: {e}")

            return [
                PriorityProductDB(
                    exchange=exchange.lower(),
                    symbol=symbol,
                    apy=0.0,
                    is_active=False,
                    product_id=None,
                    lock_period_days=0,
                )
                for symbol in PriorityProductCRUD.SYMBOL_ORDER
            ]

    @staticmethod
    async def upsert_priority_product(
        db: AsyncSession,
        exchange: str,
        symbol: str,
        apy: float,
        is_active: bool = True,
        product_id: Optional[str] = None,
        lock_period_days: int = 0,
    ) -> PriorityProductDB:
        try:
            result = await db.execute(
                select(PriorityProductDB).where(
                    and_(
                        PriorityProductDB.exchange == exchange.lower(),
                        PriorityProductDB.symbol == symbol.upper(),
                    )
                )
            )
            existing = result.scalar_one_or_none()

            now = datetime.now(UTC).replace(tzinfo=None)

            if existing:
                existing.apy = apy
                existing.is_active = is_active
                existing.product_id = product_id
                existing.lock_period_days = lock_period_days
                existing.updated_at = now
                await db.commit()
                await db.refresh(existing)
                return existing
            else:
                new_product = PriorityProductDB(
                    exchange=exchange.lower(),
                    symbol=symbol.upper(),
                    apy=apy,
                    is_active=is_active,
                    product_id=product_id,
                    lock_period_days=lock_period_days,
                    created_at=now,
                    updated_at=now,
                )
                db.add(new_product)
                await db.commit()
                await db.refresh(new_product)
                return new_product

        except Exception as e:
            logger.error(f"Помилка upsert priority продукту {exchange}/{symbol}: {e}")
            await db.rollback()
            raise

    @staticmethod
    async def get_all_priority_products(db: AsyncSession) -> List[PriorityProductDB]:
        try:
            result = await db.execute(
                select(PriorityProductDB).order_by(
                    PriorityProductDB.exchange, PriorityProductDB.symbol
                )
            )
            return result.scalars().all()
        except Exception as e:
            logger.error(f"Помилка отримання всіх priority продуктів: {e}")
            return []
