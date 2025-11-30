"""
CRUD операції для роботи з базою даних.

Цей модуль містить функції для Create, Read, Update, Delete
операцій з усіма таблицями бази даних.
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func, and_, or_, desc, asc
from sqlalchemy.orm import selectinload
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timedelta, UTC
import json

from app.db.models import (
    YieldProductDB, ExchangeDataDB, CacheMetadataDB,
    UserAnalyticsDB, SystemMetricsDB, APILogsDB, CoinsPopularityDB,
    PriorityProductDB
)
from app.db.database import get_database_session
from sqlalchemy import case
from sqlalchemy.sql import func
from app.models.yield_product import YieldProduct, YieldProductCreate, YieldProductUpdate, YieldProductFilter
from app.utils.logger import logger


# =============================================================================
# YIELD PRODUCTS CRUD OPERATIONS
# =============================================================================

class YieldProductCRUD:
    """CRUD операції для Yield продуктів."""
    
    @staticmethod
    async def create_product(db: AsyncSession, product_data: YieldProductCreate) -> YieldProductDB:
        """
        Створює новий Yield продукт.
        
        Args:
            db: Сесія бази даних
            product_data: Дані для створення продукту
            
        Returns:
            YieldProductDB: Створений продукт
        """
        try:
            # Створюємо унікальний ID
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
                raw_data=product_data.raw_data
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
        """
        Отримує продукт за ID.
        
        Args:
            db: Сесія бази даних
            product_id: ID продукту
            
        Returns:
            Optional[YieldProductDB]: Продукт або None
        """
        try:
            result = await db.execute(
                select(YieldProductDB).where(YieldProductDB.id == product_id)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Помилка отримання продукту {product_id}: {e}")
            return None
    
    @staticmethod
    async def get_products_by_symbol(db: AsyncSession, symbol: str) -> List[YieldProductDB]:
        """
        Отримує всі продукти по символу монети.
        
        Args:
            db: Сесія бази даних
            symbol: Символ монети (BTC, ETH)
            
        Returns:
            List[YieldProductDB]: Список продуктів
        """
        try:
            logger.info(f"🔍 Виконуємо запит до БД: SELECT * FROM yield_products WHERE symbol = '{symbol.upper()}' ORDER BY apy DESC")
            result = await db.execute(
                select(YieldProductDB)
                .where(YieldProductDB.symbol == symbol.upper())
                .order_by(desc(YieldProductDB.apy))
            )
            products = result.scalars().all()
            logger.info(f"📊 БД повернула {len(products)} продуктів для {symbol}: {[f'{p.provider}:{p.name}' for p in products[:3]]}")
            return products
        except Exception as e:
            logger.error(f"Помилка отримання продуктів по символу {symbol}: {e}")
            return []
    
    @staticmethod
    async def get_products_by_provider(db: AsyncSession, provider: str) -> List[YieldProductDB]:
        """
        Отримує всі продукти по провайдеру.
        
        Args:
            db: Сесія бази даних
            provider: Провайдер (Binance, Bybit)
            
        Returns:
            List[YieldProductDB]: Список продуктів
        """
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
        db: AsyncSession, 
        symbol: str, 
        provider: str
    ) -> List[YieldProductDB]:
        """
        Отримує продукти по символу та провайдеру.
        
        Args:
            db: Сесія бази даних
            symbol: Символ монети (BTC, ETH)
            provider: Провайдер (Binance, Bybit) - точна назва з БД
            
        Returns:
            List[YieldProductDB]: Список продуктів
        """
        try:
            # Використовуємо точне порівняння (без ilike) для кращої продуктивності
            # Provider в БД зберігається з великої літери (Binance, Bybit)
            result = await db.execute(
                select(YieldProductDB)
                .where(YieldProductDB.symbol == symbol.upper())
                .where(YieldProductDB.provider == provider)  # Точне порівняння
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
        """
        Отримує всі продукти з пагінацією.

        Args:
            limit: Ліміт записів
            offset: Зміщення

        Returns:
            List[YieldProductDB]: Список продуктів
        """
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

                logger.info(f"✅ Знайдено {len(products)} активних продуктів в БД (limit={limit}, offset={offset})")
                return products
            except Exception as e:
                logger.error(f"Помилка отримання всіх продуктів: {e}")
                return []
    
    @staticmethod
    async def get_all_products_sorted_by_popularity(
        limit: Optional[int] = None,
        offset: int = 0,
        filters: Optional[YieldProductFilter] = None
    ) -> List[YieldProductDB]:
        """
        Отримує продукти відсортовані за популярністю з CoinGecko через оптимізований JOIN.
        
        Використовує LEFT JOIN до coins_popularity для ефективного сортування.
        
        Args:
            limit: Ліміт записів
            offset: Зміщення
            filters: Фільтри для продуктів
            
        Returns:
            List[YieldProductDB]: Відсортовані продукти
        """
        async with get_database_session() as db:
            try:
                logger.info(f"🔍 Отримання продуктів з сортуванням за популярністю: limit={limit}, offset={offset}")
                
                # Створюємо JOIN запит
                # ВАЖЛИВО: Використовуємо func.upper() для порівняння символів, бо в БД можуть бути різні регістри
                query = (
                    select(YieldProductDB)
                    .outerjoin(
                        CoinsPopularityDB,
                        func.upper(YieldProductDB.symbol) == func.upper(CoinsPopularityDB.symbol)
                    )
                    .where(YieldProductDB.is_active == True)
                )
                
                # Застосовуємо фільтри якщо є
                if filters:
                    if filters.symbol:
                        query = query.where(YieldProductDB.symbol == filters.symbol.upper())
                    if filters.provider:
                        query = query.where(YieldProductDB.provider == filters.provider)
                    if filters.min_apy is not None:
                        query = query.where(YieldProductDB.apy >= filters.min_apy)
                    if filters.max_apy is not None:
                        query = query.where(YieldProductDB.apy <= filters.max_apy)
                    if filters.lock_period_days is not None:
                        query = query.where(YieldProductDB.lock_period_days == filters.lock_period_days)
                
                # Сортуємо за популярністю (менший rank = популярніший)
                # ВАЖЛИВО: Використовуємо явний SQL для сортування, бо SQLAlchemy може неправильно обробляти func.coalesce() в JOIN
                # Використовуємо COALESCE для монет без рейтингу (9999 = в кінець)
                from sqlalchemy import text
                query = query.order_by(
                    text("COALESCE(coins_popularity.market_cap_rank, 9999) ASC"),
                    YieldProductDB.apy.desc()  # Вторинне сортування за APY
                )
                
                # Застосовуємо пагінацію
                if limit is not None:
                    query = query.limit(limit).offset(offset)
                else:
                    query = query.offset(offset)
                
                result = await db.execute(query)
                # ВАЖЛИВО: unique() може порушити порядок сортування при JOIN
                # Спочатку отримуємо всі результати, потім видаляємо дублікати вручну зі збереженням порядку
                all_results = result.scalars().all()
                
                # Видаляємо дублікати зі збереженням порядку (за product_id)
                seen_ids = set()
                products = []
                for product in all_results:
                    if product.id not in seen_ids:
                        seen_ids.add(product.id)
                        products.append(product)
                
                # Перевірка: логуємо перші 5 продуктів для дебагу сортування
                if products and len(products) >= 5:
                    logger.info(f"🔍 Перші 5 продуктів після сортування: {[(p.symbol, p.provider, p.apy) for p in products[:5]]}")
                
                # Додаткова перевірка: логуємо перші 5 продуктів для дебагу
                if products:
                    logger.info(f"✅ Знайдено {len(products)} продуктів з сортуванням за популярністю")
                    # Перевіряємо чи є дані про популярність у перших продуктах
                    if len(products) > 0:
                        first_product = products[0]
                        logger.debug(f"🔍 Перший продукт після сортування: {first_product.symbol} ({first_product.provider}), APY: {first_product.apy}")
                else:
                    logger.warning("⚠️ JOIN не повернув жодних продуктів")
                
                return products
                
            except Exception as e:
                logger.error(f"Помилка отримання продуктів за популярністю: {e}", exc_info=True)
                return []
    
    @staticmethod
    async def get_top_products(db: AsyncSession, limit: int = 20) -> List[YieldProductDB]:
        """
        Отримує топ продуктів за APY.

        Args:
            db: Сесія бази даних
            limit: Кількість продуктів

        Returns:
            List[YieldProductDB]: Топ продуктів
        """
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

    async def get_top_products_by_provider(db: AsyncSession, limit_per_provider: int = 10) -> Dict[str, List[YieldProductDB]]:
        """
        Отримує топ продуктів за APY для кожної біржі окремо.

        Args:
            db: Сесія бази даних
            limit_per_provider: Кількість продуктів на біржу

        Returns:
            Dict[str, List[YieldProductDB]]: Топ продуктів згруповані по provider'у
        """
        try:
            # Отримуємо унікальні provider'и
            providers_result = await db.execute(
                select(YieldProductDB.provider.distinct())
                .where(YieldProductDB.is_active == True)
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
                if products:  # Додаємо тільки якщо є продукти
                    result[provider] = products

            logger.info(f"📊 Отримано топ продукти по {len(result)} біржам: {list(result.keys())}")
            return result
        except Exception as e:
            logger.error(f"Помилка отримання топ продуктів по provider'ам: {e}")
            return {}

    @staticmethod
    async def get_products_sorted_by_popularity(
        db: AsyncSession,
        limit: int = 100,
        offset: int = 0
    ) -> List[YieldProductDB]:
        """
        Отримує продукти відсортовані за популярністю монет з CoinGecko.

        Виконує LEFT JOIN з таблицею coins_popularity і сортує за market_cap_rank.
        Для монет без рейтингу встановлює рейтинг 9999 (в кінець списку).

        Args:
            db: Сесія бази даних
            limit: Ліміт записів
            offset: Зміщення

        Returns:
            List[YieldProductDB]: Список продуктів відсортований за популярністю
        """
        try:
            logger.info("🔍 Починаємо створення запиту сортування за популярністю")
            # Створюємо запит з LEFT JOIN і сортуванням за популярністю
            query = (
                select(YieldProductDB)
                .outerjoin(
                    CoinsPopularityDB,
                    func.upper(YieldProductDB.symbol) == func.upper(CoinsPopularityDB.symbol)
                )
                .where(YieldProductDB.is_active == True)
                .order_by(
                    # Сортуємо за рейтингу популярності (ASC: популярні перші)
                    # Якщо рейтинг відсутній, використовуємо 9999
                    func.coalesce(CoinsPopularityDB.market_cap_rank, 9999).asc(),
                    # Додаткове сортування за APY в межах однакового рейтингу
                    desc(YieldProductDB.apy)
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
            logger.error(f"❌ Помилка отримання продуктів відсортованих за популярністю: {e}", exc_info=True)
            return []

    @staticmethod
    async def get_products_by_provider_sorted_by_popularity(
        db: AsyncSession,
        provider: str,
        limit: int = 50
    ) -> List[YieldProductDB]:
        """
        Отримує продукти конкретного провайдера відсортовані за популярністю монет.

        Args:
            db: Сесія бази даних
            provider: Назва провайдера (Binance, Bybit)
            limit: Ліміт записів

        Returns:
            List[YieldProductDB]: Список продуктів провайдера відсортований за популярністю
        """
        try:
            query = (
                select(YieldProductDB)
                .outerjoin(
                    CoinsPopularityDB,
                    func.upper(YieldProductDB.symbol) == func.upper(CoinsPopularityDB.symbol)
                )
                .where(YieldProductDB.is_active == True)
                .where(YieldProductDB.provider == provider)
                .order_by(
                    func.coalesce(CoinsPopularityDB.market_cap_rank, 9999).asc(),
                    desc(YieldProductDB.apy)
                )
                .limit(limit)
            )

            logger.info(f"🔍 Отримуємо продукти {provider} відсортовані за популярністю")
            logger.info("🔍 Виконуємо SQL запит до БД...")
            result = await db.execute(query)
            products = result.scalars().all()
            logger.info(f"🔍 SQL запит виконано, отримано {len(products)} продуктів")

            logger.info(f"✅ Отримано {len(products)} продуктів {provider} за популярністю")
            return products

        except Exception as e:
            logger.error(f"Помилка отримання продуктів {provider} за популярністю: {e}")
            return []

    @staticmethod
    async def filter_products(filters: YieldProductFilter, limit: Optional[int] = None) -> List[YieldProductDB]:
        """
        Фільтрує продукти за критеріями.

        Args:
            filters: Фільтри
            limit: Максимальна кількість продуктів (None для всіх)

        Returns:
            List[YieldProductDB]: Відфільтровані продукти
        """
        async with get_database_session() as db:
            try:
                query = select(YieldProductDB).where(YieldProductDB.is_active == True)

                # Застосовуємо фільтри
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
    async def update_product(db: AsyncSession, product_id: str, update_data: YieldProductUpdate) -> Optional[YieldProductDB]:
        """
        Оновлює продукт.
        
        Args:
            db: Сесія бази даних
            product_id: ID продукту
            update_data: Дані для оновлення
            
        Returns:
            Optional[YieldProductDB]: Оновлений продукт або None
        """
        try:
            # Отримуємо продукт
            product = await YieldProductCRUD.get_product_by_id(db, product_id)
            if not product:
                return None
            
            # Оновлюємо поля
            # Pydantic v2: використовуємо model_dump
            try:
                update_dict = update_data.model_dump(exclude_unset=True)
            except AttributeError:
                # Backward-compatible fallback
                update_dict = update_data.dict(exclude_unset=True)
            if update_dict:
                # Завжди оновлюємо updated_at при будь-якому оновленні
                update_dict['updated_at'] = datetime.now(UTC).replace(tzinfo=None)
                
                await db.execute(
                    update(YieldProductDB)
                    .where(YieldProductDB.id == product_id)
                    .values(**update_dict)
                )
                await db.commit()
                await db.refresh(product)
                
                # Отримуємо оновлений продукт
                return await YieldProductCRUD.get_product_by_id(db, product_id)
            
            return product
        except Exception as e:
            logger.error(f"Помилка оновлення продукту {product_id}: {e}")
            await db.rollback()
            return None
    
    @staticmethod
    async def delete_product(db: AsyncSession, product_id: str) -> bool:
        """
        Видаляє продукт.
        
        Args:
            db: Сесія бази даних
            product_id: ID продукту
            
        Returns:
            bool: Чи успішно видалено
        """
        try:
            await db.execute(
                delete(YieldProductDB).where(YieldProductDB.id == product_id)
            )
            await db.commit()
            logger.info(f"Видалено продукт: {product_id}")
            return True
        except Exception as e:
            logger.error(f"Помилка видалення продукту {product_id}: {e}")
            await db.rollback()
            return False
    
    @staticmethod
    async def bulk_create_products(db: AsyncSession, products_data: List[YieldProductCreate]) -> List[YieldProductDB]:
        """
        Масове створення продуктів.
        
        Args:
            db: Сесія бази даних
            products_data: Список даних для створення
            
        Returns:
            List[YieldProductDB]: Створені продукти
        """
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
                    raw_data=product_data.raw_data
                )
                created_products.append(db_product)
                db.add(db_product)
            
            await db.commit()
            
            # Оновлюємо всі продукти
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
        """
        Отримує загальну кількість продуктів.

        Args:
            db: Сесія бази даних
            active_only: Чи рахувати тільки активні продукти (за замовчуванням True)

        Returns:
            int: Кількість продуктів
        """
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
    """CRUD операції для даних з бірж."""
    
    @staticmethod
    async def create_exchange_data(
        db: AsyncSession, 
        product_id: str, 
        exchange: str, 
        raw_data: Dict[str, Any],
        api_endpoint: str = None,
        response_status: int = None,
        response_time_ms: int = None,
        request_timestamp: Optional[datetime] = None
    ) -> ExchangeDataDB:
        """
        Створює запис даних з біржі.
        
        Args:
            db: Сесія бази даних
            product_id: ID продукту
            exchange: Назва біржі
            raw_data: Сирі дані з API
            api_endpoint: API endpoint
            response_status: HTTP статус
            response_time_ms: Час відповіді
            
        Returns:
            ExchangeDataDB: Створений запис
        """
        try:
            db_exchange_data = ExchangeDataDB(
                product_id=product_id,
                exchange=exchange,
                raw_data=raw_data,
                api_endpoint=api_endpoint,
                response_status=response_status,
                response_time_ms=response_time_ms
            )
            
            # Якщо передано request_timestamp, встановлюємо його вручну
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
    async def get_exchange_data_by_product(db: AsyncSession, product_id: str) -> List[ExchangeDataDB]:
        """
        Отримує дані з бірж по продукту.
        
        Args:
            db: Сесія бази даних
            product_id: ID продукту
            
        Returns:
            List[ExchangeDataDB]: Список даних з бірж
        """
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
    async def get_exchange_data_by_exchange(db: AsyncSession, exchange: str) -> List[ExchangeDataDB]:
        """
        Отримує дані з конкретної біржі.
        
        Args:
            db: Сесія бази даних
            exchange: Назва біржі
            
        Returns:
            List[ExchangeDataDB]: Список даних
        """
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
    async def get_latest_exchange_data(db: AsyncSession, exchange: str, limit: int = 100) -> List[ExchangeDataDB]:
        """
        Отримує останні дані з біржі.
        
        Args:
            db: Сесія бази даних
            exchange: Назва біржі
            limit: Ліміт записів
            
        Returns:
            List[ExchangeDataDB]: Останні дані
        """
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
    """CRUD операції для метаданих кешу."""
    
    @staticmethod
    async def create_cache_metadata(
        db: AsyncSession,
        cache_key: str,
        cache_type: str,
        expires_at: datetime,
        data_size_bytes: int = None
    ) -> CacheMetadataDB:
        """
        Створює метадані кешу.
        
        Args:
            db: Сесія бази даних
            cache_key: Ключ кешу
            cache_type: Тип кешу
            expires_at: Час закінчення
            data_size_bytes: Розмір даних
            
        Returns:
            CacheMetadataDB: Створені метадані
        """
        try:
            db_cache_metadata = CacheMetadataDB(
                cache_key=cache_key,
                cache_type=cache_type,
                expires_at=expires_at,
                data_size_bytes=data_size_bytes
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
        """
        Отримує метадані кешу за ключем.
        
        Args:
            db: Сесія бази даних
            cache_key: Ключ кешу
            
        Returns:
            Optional[CacheMetadataDB]: Метадані або None
        """
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
        """
        Оновлює статистику доступу до кешу.
        
        Args:
            db: Сесія бази даних
            cache_key: Ключ кешу
            is_hit: Чи попадання в кеш
            
        Returns:
            bool: Чи успішно оновлено
        """
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
        """
        Отримує ключі кешу, що закінчилися.
        
        Args:
            db: Сесія бази даних
            
        Returns:
            List[str]: Список ключів
        """
        try:
            result = await db.execute(
                select(CacheMetadataDB.cache_key)
                .where(CacheMetadataDB.expires_at < datetime.now(UTC).replace(tzinfo=None))
            )
            return [row[0] for row in result.fetchall()]
        except Exception as e:
            logger.error(f"Помилка отримання закінчених ключів кешу: {e}")
            return []
    
    @staticmethod
    async def delete_expired_cache(db: AsyncSession) -> int:
        """
        Видаляє закінчені записи кешу.
        
        Args:
            db: Сесія бази даних
            
        Returns:
            int: Кількість видалених записів
        """
        try:
            result = await db.execute(
                delete(CacheMetadataDB)
                .where(CacheMetadataDB.expires_at < datetime.now(UTC).replace(tzinfo=None))
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
        """
        Отримує статистику кешу.
        
        Args:
            db: Сесія бази даних
            
        Returns:
            Dict[str, Any]: Статистика кешу
        """
        try:
            # Загальна статистика
            total_result = await db.execute(
                select(func.count(CacheMetadataDB.id))
            )
            total_count = total_result.scalar() or 0
            
            # Статистика по типах
            type_result = await db.execute(
                select(
                    CacheMetadataDB.cache_type,
                    func.count(CacheMetadataDB.id).label('count')
                )
                .group_by(CacheMetadataDB.cache_type)
            )
            type_stats = {row[0]: row[1] for row in type_result.fetchall()}
            
            # Загальна статистика попадань
            hit_result = await db.execute(
                select(
                    func.sum(CacheMetadataDB.hit_count).label('total_hits'),
                    func.sum(CacheMetadataDB.miss_count).label('total_misses')
                )
            )
            hit_row = hit_result.fetchone()
            total_hits = hit_row[0] or 0
            total_misses = hit_row[1] or 0
            total_requests = total_hits + total_misses
            hit_rate = (total_hits / total_requests * 100) if total_requests > 0 else 0
            
            return {
                'total_cache_entries': total_count,
                'cache_types': type_stats,
                'total_hits': total_hits,
                'total_misses': total_misses,
                'total_requests': total_requests,
                'hit_rate_percent': round(hit_rate, 2)
            }
            
        except Exception as e:
            logger.error(f"Помилка отримання статистики кешу: {e}")
            return {}


# =============================================================================
# BULK OPERATIONS
# =============================================================================

class BulkOperations:
    """Масові операції з даними."""
    
    @staticmethod
    async def bulk_upsert_products(db: AsyncSession, products_data: List[Dict[str, Any]]) -> Tuple[int, int]:
        """
        Масове оновлення/вставка продуктів.
        
        Args:
            db: Сесія бази даних
            products_data: Список даних продуктів
            
        Returns:
            Tuple[int, int]: (кількість оновлених, кількість створених)
        """
        try:
            updated_count = 0
            created_count = 0
            
            for product_data in products_data:
                # Перевіряємо чи існує продукт
                existing_product = await YieldProductCRUD.get_product_by_id(db, product_data['id'])
                
                if existing_product:
                    # Оновлюємо існуючий
                    update_data = YieldProductUpdate(**product_data)
                    await YieldProductCRUD.update_product(db, product_data['id'], update_data)
                    updated_count += 1
                else:
                    # Створюємо новий
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
        db: AsyncSession, 
        exchange_data_list: List[Dict[str, Any]]
    ) -> int:
        """
        Масове створення даних з бірж.
        
        Args:
            db: Сесія бази даних
            exchange_data_list: Список даних з бірж
            
        Returns:
            int: Кількість створених записів
        """
        try:
            created_count = 0
            
            for data in exchange_data_list:
                await ExchangeDataCRUD.create_exchange_data(
                    db=db,
                    product_id=data['product_id'],
                    exchange=data['exchange'],
                    raw_data=data['raw_data'],
                    api_endpoint=data.get('api_endpoint'),
                    response_status=data.get('response_status'),
                    response_time_ms=data.get('response_time_ms')
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
        """
        Очищає старі дані.
        
        Args:
            db: Сесія бази даних
            days_old: Вік даних в днях
            
        Returns:
            Dict[str, int]: Кількість видалених записів по таблицях
        """
        try:
            cutoff_date = datetime.now(UTC).replace(tzinfo=None) - timedelta(days=days_old)
            deleted_counts = {}
            
            # Видаляємо старі дані з бірж
            exchange_result = await db.execute(
                delete(ExchangeDataDB)
                .where(ExchangeDataDB.request_timestamp < cutoff_date)
            )
            deleted_counts['exchange_data'] = exchange_result.rowcount
            
            # Видаляємо закінчені записи кешу
            cache_result = await db.execute(
                delete(CacheMetadataDB)
                .where(CacheMetadataDB.expires_at < cutoff_date)
            )
            deleted_counts['cache_metadata'] = cache_result.rowcount
            
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
    """CRUD операції для рейтингу популярності монет з CoinGecko."""

    @staticmethod
    async def create_or_update_coins_popularity(
        db: AsyncSession,
        popularity_data: Dict[str, Any]
    ) -> CoinsPopularityDB:
        """
        Створює або оновлює запис популярності монети.

        Args:
            db: Сесія бази даних
            popularity_data: Дані монети з CoinGecko

        Returns:
            CoinsPopularityDB: Створений або оновлений запис
        """
        try:
            # Спробуємо знайти існуючий запис за coin_id або symbol
            existing_record = await db.execute(
                select(CoinsPopularityDB).where(
                    or_(
                        CoinsPopularityDB.coin_id == popularity_data["coin_id"],
                        CoinsPopularityDB.symbol == popularity_data["symbol"]
                    )
                )
            )
            existing = existing_record.scalar_one_or_none()

            if existing:
                # Оновлюємо існуючий запис
                for key, value in popularity_data.items():
                    if hasattr(existing, key):
                        setattr(existing, key, value)
                logger.debug(f"Оновлено популярність для {popularity_data['symbol']}")
                return existing
            else:
                # Створюємо новий запис
                db_record = CoinsPopularityDB(**popularity_data)
                db.add(db_record)
                logger.debug(f"Створено новий запис популярності для {popularity_data['symbol']}")
                return db_record

        except Exception as e:
            logger.error(f"Помилка створення/оновлення популярності для {popularity_data.get('symbol', '?')}: {e}")
            raise

    @staticmethod
    async def get_popularity_by_symbol(
        db: AsyncSession,
        symbol: str
    ) -> Optional[CoinsPopularityDB]:
        """
        Отримує рейтинг популярності за символом монети.

        Args:
            db: Сесія бази даних
            symbol: Символ монети (BTC, ETH, тощо)

        Returns:
            Optional[CoinsPopularityDB]: Запис популярності або None
        """
        try:
            normalized_symbol = symbol.upper()

            result = await db.execute(
                select(CoinsPopularityDB).where(
                    CoinsPopularityDB.symbol == normalized_symbol
                )
            )
            return result.scalar_one_or_none()

        except Exception as e:
            logger.error(f"Помилка отримання популярності для {symbol}: {e}")
            return None

    @staticmethod
    async def get_popularity_rank(db: AsyncSession, symbol: str) -> Optional[int]:
        """
        Отримує тільки рейтинг популярності за символом монети.

        Args:
            db: Сесія бази даних
            symbol: Символ монети

        Returns:
            Optional[int]: Рейтинг популярності або None
        """
        record = await CoinsPopularityCRUD.get_popularity_by_symbol(db, symbol)
        return record.market_cap_rank if record else None

    @staticmethod
    async def get_top_popular_coins(
        db: AsyncSession,
        limit: int = 10
    ) -> List[CoinsPopularityDB]:
        """
        Отримує топ популярних монет за рейтингом.

        Args:
            db: Сесія бази даних
            limit: Кількість монет для повернення

        Returns:
            List[CoinsPopularityDB]: Список топ монет
        """
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
        """
        Отримує статистику по даним популярності.

        Args:
            db: Сесія бази даних

        Returns:
            Dict[str, Any]: Статистика
        """
        try:
            # Загальна кількість монет
            total_result = await db.execute(
                select(func.count(CoinsPopularityDB.id))
            )
            total_coins = total_result.scalar() or 0

            # Останнє оновлення
            last_update_result = await db.execute(
                select(func.max(CoinsPopularityDB.updated_at))
            )
            last_update = last_update_result.scalar()

            # Топ-5 монет
            top_result = await db.execute(
                select(CoinsPopularityDB.symbol, CoinsPopularityDB.market_cap_rank)
                .order_by(asc(CoinsPopularityDB.market_cap_rank))
                .limit(5)
            )
            top_coins = top_result.all()

            return {
                "total_coins": total_coins,
                "last_update": last_update.isoformat() if last_update else None,
                "top_coins": [{"symbol": coin[0], "rank": coin[1]} for coin in top_coins]
            }

        except Exception as e:
            logger.error(f"Помилка отримання статистики популярності: {e}")
            return {
                "total_coins": 0,
                "last_update": None,
                "top_coins": []
            }

    @staticmethod
    async def clear_old_popularity_data(
        db: AsyncSession,
        days_to_keep: int = 30
    ) -> int:
        """
        Очищає старі дані популярності.

        Args:
            db: Сесія бази даних
            days_to_keep: Кількість днів для зберігання

        Returns:
            int: Кількість видалених записів
        """
        try:
            cutoff_date = datetime.now(UTC).replace(tzinfo=None) - timedelta(days=days_to_keep)

            result = await db.execute(
                delete(CoinsPopularityDB)
                .where(CoinsPopularityDB.updated_at < cutoff_date)
            )

            deleted_count = result.rowcount
            logger.info(f"Видалено {deleted_count} старих записів популярності")

            return deleted_count

        except Exception as e:
            logger.error(f"Помилка очищення старих даних популярності: {e}")
            return 0


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

async def create_or_update_coins_popularity(
    db: AsyncSession,
    popularity_data: Dict[str, Any]
) -> CoinsPopularityDB:
    """
    Створює або оновлює запис популярності монети.

    Це обгортка над CoinsPopularityCRUD.create_or_update_coins_popularity
    для зручності використання.

    Args:
        db: Сесія бази даних
        popularity_data: Дані монети з CoinGecko

    Returns:
        CoinsPopularityDB: Створений або оновлений запис
    """
    return await CoinsPopularityCRUD.create_or_update_coins_popularity(db, popularity_data)


async def get_products_sorted_by_popularity(
    limit: int = 100,
    offset: int = 0
) -> List[YieldProductDB]:
    """
    Отримує продукти відсортовані за популярністю монет з CoinGecko.

    Це обгортка над YieldProductCRUD.get_products_sorted_by_popularity
    для зручності використання.

    Args:
        limit: Ліміт записів
        offset: Зміщення

    Returns:
        List[YieldProductDB]: Список продуктів відсортований за популярністю
    """
    async with get_database_session() as session:
        return await YieldProductCRUD.get_products_sorted_by_popularity(
            session, limit=limit, offset=offset
        )


async def get_products_by_provider_sorted_by_popularity(
    provider: str,
    limit: int = 50
) -> List[YieldProductDB]:
    """
    Отримує продукти конкретного провайдера відсортовані за популярністю монет.

    Це обгортка над YieldProductCRUD.get_products_by_provider_sorted_by_popularity
    для зручності використання.

    Args:
        provider: Назва провайдера (Binance, Bybit)
        limit: Ліміт записів

    Returns:
        List[YieldProductDB]: Список продуктів провайдера відсортований за популярністю
    """
    async with get_database_session() as session:
        return await YieldProductCRUD.get_products_by_provider_sorted_by_popularity(
            session, provider=provider, limit=limit
        )


async def get_database_stats(db: AsyncSession) -> Dict[str, Any]:
    """
    Отримує статистику бази даних.
    
    Args:
        db: Сесія бази даних
        
    Returns:
        Dict[str, Any]: Статистика БД
    """
    try:
        stats = {}
        
        # Кількість активних продуктів (тільки ті, що відображаються в API)
        active_products_count = await YieldProductCRUD.get_products_count(db, active_only=True)
        stats['total_products'] = active_products_count
        
        # Статистика кешу
        cache_stats = await CacheMetadataCRUD.get_cache_statistics(db)
        stats.update(cache_stats)
        
        # Кількість даних з бірж
        exchange_result = await db.execute(
            select(func.count(ExchangeDataDB.id))
        )
        stats['total_exchange_data'] = exchange_result.scalar() or 0
        
        return stats
        
    except Exception as e:
        logger.error(f"Помилка отримання статистики БД: {e}")
        return {}


# =============================================================================
# PRIORITY PRODUCTS CRUD OPERATIONS
# =============================================================================

class PriorityProductCRUD:
    """CRUD операції для Priority продуктів (BTC, ETH, SOL, USDT)."""
    
    # Порядок символів для виведення
    SYMBOL_ORDER = ["BTC", "ETH", "SOL", "USDT"]
    
    @staticmethod
    async def get_priority_products_by_exchange(
        db: AsyncSession, 
        exchange: str
    ) -> List[PriorityProductDB]:
        """
        Отримує всі 4 продукти (BTC, ETH, SOL, USDT) для біржі в правильному порядку.
        
        Args:
            db: Сесія бази даних
            exchange: Назва біржі (binance, bybit)
            
        Returns:
            List[PriorityProductDB]: Список з 4 продуктів в порядку BTC, ETH, SOL, USDT
        """
        try:
            result = await db.execute(
                select(PriorityProductDB)
                .where(PriorityProductDB.exchange == exchange.lower())
            )
            products = result.scalars().all()
            
            # Створюємо словник для швидкого пошуку
            products_dict = {p.symbol: p for p in products}
            
            # Повертаємо в правильному порядку, створюючи записи з APY=0.0 якщо немає
            ordered_products = []
            for symbol in PriorityProductCRUD.SYMBOL_ORDER:
                if symbol in products_dict:
                    ordered_products.append(products_dict[symbol])
                else:
                    # Створюємо запис з APY=0.0 якщо продукт не знайдено
                    ordered_products.append(
                        PriorityProductDB(
                            exchange=exchange.lower(),
                            symbol=symbol,
                            apy=0.0,
                            is_active=False,
                            product_id=None,
                            lock_period_days=0
                        )
                    )
            
            return ordered_products
            
        except Exception as e:
            logger.error(f"Помилка отримання priority продуктів для {exchange}: {e}")
            # Повертаємо 4 записи з APY=0.0 при помилці
            return [
                PriorityProductDB(
                    exchange=exchange.lower(),
                    symbol=symbol,
                    apy=0.0,
                    is_active=False,
                    product_id=None,
                    lock_period_days=0
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
        lock_period_days: int = 0
    ) -> PriorityProductDB:
        """
        Оновлює або створює запис priority продукту.
        
        Args:
            db: Сесія бази даних
            exchange: Назва біржі
            symbol: Символ токену (BTC, ETH, SOL, USDT)
            apy: APY у відсотках
            is_active: Чи активний продукт
            product_id: ID продукту з yield_products
            lock_period_days: Період блокування
            
        Returns:
            PriorityProductDB: Оновлений або створений продукт
        """
        try:
            # Перевіряємо чи існує запис
            result = await db.execute(
                select(PriorityProductDB)
                .where(
                    and_(
                        PriorityProductDB.exchange == exchange.lower(),
                        PriorityProductDB.symbol == symbol.upper()
                    )
                )
            )
            existing = result.scalar_one_or_none()
            
            now = datetime.now(UTC).replace(tzinfo=None)
            
            if existing:
                # Оновлюємо існуючий запис
                existing.apy = apy
                existing.is_active = is_active
                existing.product_id = product_id
                existing.lock_period_days = lock_period_days
                existing.updated_at = now
                await db.commit()
                await db.refresh(existing)
                return existing
            else:
                # Створюємо новий запис
                new_product = PriorityProductDB(
                    exchange=exchange.lower(),
                    symbol=symbol.upper(),
                    apy=apy,
                    is_active=is_active,
                    product_id=product_id,
                    lock_period_days=lock_period_days,
                    created_at=now,
                    updated_at=now
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
    async def get_all_priority_products(
        db: AsyncSession
    ) -> List[PriorityProductDB]:
        """
        Отримує всі priority продукти (для API).
        
        Args:
            db: Сесія бази даних
            
        Returns:
            List[PriorityProductDB]: Список всіх priority продуктів
        """
        try:
            result = await db.execute(
                select(PriorityProductDB)
                .order_by(PriorityProductDB.exchange, PriorityProductDB.symbol)
            )
            return result.scalars().all()
        except Exception as e:
            logger.error(f"Помилка отримання всіх priority продуктів: {e}")
            return []
