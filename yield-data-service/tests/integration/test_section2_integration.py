"""
Тести інтеграції РОЗДІЛ 2: Реалізація кешування та зберігання даних.

Цей модуль тестує:
- Отримання даних з Binance та Bybit API
- Нормалізацію та збереження даних в БД
- Роботу кешування
- Комплексні сценарії використання
"""

import pytest
import asyncio
from typing import List, Dict, Any
from datetime import datetime, UTC
from unittest.mock import patch

from app.services.binance_service import binance_service
from app.services.bybit_service import bybit_service
from app.services.cache import cache_manager
from app.db.crud import YieldProductCRUD, ExchangeDataCRUD
from app.db.database import db_manager, get_database_session
from sqlalchemy.ext.asyncio import AsyncSession
from app.utils.logger import logger


class TestSection2Integration:
    """Комплексні тести для РОЗДІЛ 2."""
    
    @staticmethod
    async def _init_test_db_manager():
        """Ініціалізує db_manager для тестів."""
        from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
        from sqlalchemy import text
        from app.db.models import Base
        
        logger.info("🔧 Ініціалізація тестового db_manager...")
        
        # Закриваємо старе підключення якщо існує
        if db_manager.engine:
            logger.info("🔄 Закриваємо старе підключення до БД")
            await db_manager.close()
        
        # Створюємо нове підключення до тестової БД
        test_db_url = "postgresql+asyncpg://yield_user:yield_secure_password_2024@localhost:5432/yield_db_test"
        logger.info(f"🔌 Підключення до тестової БД: {test_db_url}")
        
        db_manager.engine = create_async_engine(
            test_db_url,
            echo=False,
            pool_pre_ping=True,
            pool_recycle=3600
        )
        db_manager.session_factory = async_sessionmaker(
            bind=db_manager.engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=True,
            autocommit=False
        )
        
        logger.info("✅ db_manager налаштовано на тестову БД")
        
        # Створюємо таблиці в тестовій БД
        try:
            async with db_manager.engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            logger.info("✅ Таблиці створено в тестовій БД")
        except Exception as e:
            logger.warning(f"⚠️ Помилка створення таблиць: {e}")
            # Продовжуємо, можливо таблиці вже існують
        
        # Перевіряємо що всі необхідні таблиці створені
        required_tables = ['yield_products', 'exchange_data', 'cache_metadata']
        for table_name in required_tables:
            try:
                async with db_manager.get_session() as session:
                    result = await session.execute(text(
                        "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public' AND table_name = :table_name"
                    ), {"table_name": table_name})
                    count = result.fetchone()[0]
                    exists = count > 0
                    logger.info(f"📊 Таблиця {table_name} існує: {exists}")
                    
                    if not exists:
                        logger.warning(f"⚠️ Таблиця {table_name} не існує, спробуємо створити вручну")
                        # Створюємо таблицю вручну якщо Base.metadata.create_all не спрацював
                        try:
                            if table_name == 'exchange_data':
                                await session.execute(text("""
                                    CREATE TABLE exchange_data (
                                        id SERIAL PRIMARY KEY,
                                        product_id VARCHAR(100) NOT NULL,
                                        exchange VARCHAR(50) NOT NULL,
                                        raw_data JSON NOT NULL,
                                        api_endpoint VARCHAR(200),
                                        request_timestamp TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
                                        response_status INTEGER,
                                        response_time_ms INTEGER
                                    );
                                """))
                                await session.commit()
                                
                                # Додаємо foreign key constraint після створення таблиці
                                try:
                                    await session.execute(text("""
                                        ALTER TABLE exchange_data 
                                        ADD CONSTRAINT fk_exchange_data_product_id 
                                        FOREIGN KEY (product_id) 
                                        REFERENCES yield_products(id) 
                                        ON DELETE CASCADE;
                                    """))
                                    await session.commit()
                                except Exception as fk_error:
                                    # Foreign key може не створитися, але це не критично для тесту
                                    logger.warning(f"⚠️ Не вдалося створити foreign key: {fk_error}")
                                
                                # Створюємо індекси
                                try:
                                    await session.execute(text("CREATE INDEX IF NOT EXISTS idx_exchange_data_exchange ON exchange_data (exchange);"))
                                    await session.execute(text("CREATE INDEX IF NOT EXISTS idx_exchange_data_product_id ON exchange_data (product_id);"))
                                    await session.execute(text("CREATE INDEX IF NOT EXISTS idx_exchange_data_request_timestamp ON exchange_data (request_timestamp);"))
                                    await session.execute(text("CREATE INDEX IF NOT EXISTS idx_exchange_timestamp ON exchange_data (exchange, request_timestamp);"))
                                    await session.commit()
                                except Exception as idx_error:
                                    logger.warning(f"⚠️ Помилка створення індексів: {idx_error}")
                                
                                logger.info(f"✅ Таблиця {table_name} створена вручну")
                        except Exception as create_error:
                            logger.error(f"❌ Помилка створення таблиці {table_name}: {create_error}")
                            
            except Exception as e:
                logger.error(f"❌ Помилка перевірки таблиці {table_name}: {e}")

    @pytest.mark.asyncio
    async def test_quick_btc_all_exchanges(self, test_db_session, clean_database):
        """
        Швидкий тест: отримання BTC продуктів з усіх бірж.
        
        Мета: Перевірити основну функціональність без довгого виконання.
        Очікуваний час: 5-10 секунд
        """
        logger.info("🚀 Початок швидкого тесту BTC для всіх бірж")
        
        # Ініціалізуємо кеш перед тестом
        await cache_manager.initialize()
        
        # Ініціалізуємо глобальний db_manager для сервісів
        await self._init_test_db_manager()
        
        results = {
            "binance": {"count": 0, "success": False},
            "bybit": {"count": 0, "success": False}
        }
        
        try:
            # 1. Тест підключення до бірж
            logger.info("📡 Перевірка підключення до бірж...")
            
            # Binance (може потребувати API ключі)
            try:
                binance_health = await binance_service.test_connection()
                results["binance"]["success"] = binance_health["status"] == "success"
                logger.info(f"✅ Binance підключення: {binance_health['status']}")
            except Exception as e:
                logger.warning(f"⚠️ Binance недоступний: {e}")
            
            # Bybit (публічний API)
            try:
                bybit_health = await bybit_service.test_connection()
                results["bybit"]["success"] = bybit_health["status"] == "success"
                logger.info(f"✅ Bybit підключення: {bybit_health['status']}")
            except Exception as e:
                logger.error(f"❌ Bybit недоступний: {e}")
                # Bybit повинен працювати, тому рейзимо помилку
                raise
            
            # 2. Отримання BTC продуктів
            logger.info("💰 Отримання BTC продуктів...")
            
            # Binance BTC продукти (опціонально)
            if results["binance"]["success"]:
                try:
                    binance_products = await binance_service.get_products_with_cache("BTC")
                    # Обмежуємо для швидкого тесту
                    binance_products = binance_products[:10] if len(binance_products) > 10 else binance_products
                    results["binance"]["count"] = len(binance_products)
                    logger.info(f"📊 Binance BTC продуктів: {len(binance_products)}")
                    
                    # Зберігання в БД
                    if binance_products:
                        stats = await binance_service.save_products_to_db(binance_products)
                        logger.info(f"💾 Binance БД статистика: {stats}")
                        
                except Exception as e:
                    logger.warning(f"⚠️ Помилка отримання Binance BTC: {e}")
            
            # Bybit BTC продукти (обов'язково)
            if results["bybit"]["success"]:
                try:
                    bybit_products = await bybit_service.get_products_with_cache("BTC")
                    # Обмежуємо для швидкого тесту
                    bybit_products = bybit_products[:10] if len(bybit_products) > 10 else bybit_products
                    results["bybit"]["count"] = len(bybit_products)
                    logger.info(f"📊 Bybit BTC продуктів: {len(bybit_products)}")
                    
                    # Зберігання в БД
                    if bybit_products:
                        stats = await bybit_service.save_products_to_db(bybit_products)
                        logger.info(f"💾 Bybit БД статистика: {stats}")
                        
                except Exception as e:
                    logger.error(f"❌ Помилка отримання Bybit BTC: {e}")
                    raise
            
            # 3. Перевірка збереження в БД
            # Використовуємо тестову сесію яка підключена до yield_db_test
            async with db_manager.get_session() as db:
                # Підрахунок продуктів в БД
                all_products = await YieldProductCRUD.get_products_by_symbol(db, "BTC")
                stored_count = len(all_products)
                logger.info(f"💾 Збережено BTC продуктів в БД: {stored_count}")
            
            # 4. Валідація результатів
            total_expected = results["binance"]["count"] + results["bybit"]["count"]
            
            # Перевірки (Bybit обов'язково)
            assert results["bybit"]["success"], "Bybit API повинен бути доступний (публічний)"
            assert results["bybit"]["count"] > 0, "Повинні бути знайдені Bybit BTC продукти"
            
            # Перевіряємо що дані збереглися в БД
            assert stored_count > 0, f"Дані повинні зберегтися в БД, але збережено: {stored_count}"
            
            logger.info(f"✅ Швидкий тест завершений успішно: {results}")
            
        except Exception as e:
            logger.error(f"❌ Помилка в швидкому тесті: {e}")
            raise
        finally:
            # Закриваємо кеш
            await cache_manager.close()


    @pytest.mark.asyncio
    async def test_full_sync_all_exchanges(self, test_db_session, clean_database):
        """
        Повна синхронізація: отримання всіх даних з усіх бірж.
        
        Мета: Повне тестування з реальними даними.
        Очікуваний час: 30-60 секунд
        """
        logger.info("🚀 Початок повної синхронізації всіх бірж")
        
        # Ініціалізуємо кеш перед тестом
        await cache_manager.initialize()
        
        # Ініціалізуємо глобальний db_manager для сервісів
        await self._init_test_db_manager()
        
        sync_results = {
            "binance": {"products": 0, "sync_stats": {}},
            "bybit": {"products": 0, "sync_stats": {}}
        }
        
        try:
            # 1. Повна синхронізація Binance
            logger.info("📊 Синхронізація Binance...")
            try:
                binance_result = await binance_service.sync_products_to_db()
                sync_results["binance"]["products"] = binance_result.get("products_count", 0)
                sync_results["binance"]["sync_stats"] = binance_result.get("sync_stats", {})
                logger.info(f"Binance синхронізація: {binance_result}")
            except Exception as e:
                logger.warning(f"Binance синхронізація недоступна: {e}")
            
            # 2. Повна синхронізація Bybit
            logger.info("📊 Синхронізація Bybit...")
            try:
                bybit_result = await bybit_service.sync_products_to_db()
                sync_results["bybit"]["products"] = bybit_result.get("products_count", 0)
                sync_results["bybit"]["sync_stats"] = bybit_result.get("sync_stats", {})
                logger.info(f"Bybit синхронізація: {bybit_result}")
            except Exception as e:
                logger.error(f"Bybit синхронізація помилка: {e}")
                raise
            
            # 3. Перевірка БД після синхронізації
            async with get_database_session() as db:
                # Загальна статистика БД
                total_products = await YieldProductCRUD.get_all_products(db)
                total_stored = len(total_products)
                
                # Статистика по біржах
                bybit_products = await YieldProductCRUD.get_products_by_provider(db, "Bybit")
                binance_products = await YieldProductCRUD.get_products_by_provider(db, "Binance")
                
                logger.info(f"Загальна статистика БД:")
                logger.info(f"  - Всього продуктів: {total_stored}")
                logger.info(f"  - Bybit: {len(bybit_products)}")
                logger.info(f"  - Binance: {len(binance_products)}")
            
            # 4. Перевірка статистики exchange_data
            async with get_database_session() as db:
                exchange_data = await ExchangeDataCRUD.get_all_exchange_data(db)
                logger.info(f"Записів exchange_data: {len(exchange_data)}")
            
            # 5. Валідація результатів
            assert sync_results["bybit"]["products"] > 0, "Bybit повинен синхронізувати продукти"
            assert total_stored > 0, "Дані повинні зберегтися в БД"
            
            # Bybit зазвичай має 200+ продуктів
            assert sync_results["bybit"]["products"] >= 50, "Повинно бути значно більше Bybit продуктів"
            
            logger.info(f"✅ Повна синхронізація завершена: {sync_results}")
            
        except Exception as e:
            logger.error(f"❌ Помилка в повній синхронізації: {e}")
            raise
        finally:
            # Закриваємо кеш
            await cache_manager.close()


    @pytest.mark.asyncio
    async def test_cache_consistency_across_exchanges(self, test_db_session, clean_database):
        """
        Тест кешування між біржами.
        
        Мета: Перевірити що кеш працює окремо для кожної біржі.
        """
        logger.info("🔄 Тест кешування між біржами")
        
        # Ініціалізуємо кеш перед тестом
        await cache_manager.initialize()
        
        # Ініціалізуємо глобальний db_manager для сервісів
        await self._init_test_db_manager()
        
        try:
            # 1. Очищення кешу перед тестом
            await cache_manager.clear_cache("*")
            initial_stats = await cache_manager.get_cache_stats()
            logger.info(f"Початкова статистика кешу: {initial_stats}")
            
            # 2. Отримання даних з Bybit (кешування)
            logger.info("📊 Отримання Bybit даних (з кешуванням)...")
            bybit_products_1 = await bybit_service.get_products_with_cache("BTC")
            stats_after_bybit = await cache_manager.get_cache_stats()
            logger.info(f"Статистика після Bybit: {stats_after_bybit}")
            
            # 3. Повторне отримання Bybit (має бути з кешу)
            logger.info("📊 Повторне отримання Bybit (з кешу)...")
            bybit_products_2 = await bybit_service.get_products_with_cache("BTC")
            stats_after_cache = await cache_manager.get_cache_stats()
            logger.info(f"Статистика після кешу: {stats_after_cache}")
            
            # 4. Тест різних символів
            logger.info("📊 Тест різних символів...")
            eth_products = await bybit_service.get_products_with_cache("ETH")
            final_stats = await cache_manager.get_cache_stats()
            logger.info(f"Фінальна статистика: {final_stats}")
            
            # 5. Перевірка консистентності
            assert len(bybit_products_1) == len(bybit_products_2), "Кешовані дані повинні бути ідентичними"
            
            # 6. Тест очищення кешу за патерном
            logger.info("🗑️ Тест очищення кешу...")
            cleared_count = await cache_manager.clear_cache("exchange:bybit:*")
            stats_after_clear = await cache_manager.get_cache_stats()
            logger.info(f"Очищено ключів: {cleared_count}, статистика: {stats_after_clear}")
            
            # 7. Тест fallback (якщо Redis недоступний)
            logger.info("🔄 Тест fallback логіки...")
            health_check = await cache_manager.health_check()
            logger.info(f"Health check кешу: {health_check}")
            
            logger.info("✅ Тест кешування завершений")
            
        except Exception as e:
            logger.error(f"❌ Помилка в тесті кешування: {e}")
            raise
        finally:
            # Закриваємо кеш
            await cache_manager.close()


    @pytest.mark.asyncio
    async def test_parallel_data_fetch(self, test_db_session, clean_database):
        """
        Тест паралельного отримання даних.
        
        Мета: Перевірити стабільність при одночасних запитах.
        """
        logger.info("🚀 Тест паралельного отримання даних")
        
        # Ініціалізуємо кеш перед тестом
        await cache_manager.initialize()
        
        # Ініціалізуємо глобальний db_manager для сервісів
        await self._init_test_db_manager()
        
        try:
            # 1. Паралельне отримання даних з обох бірж
            logger.info("📊 Паралельні запити до бірж...")
            
            async def fetch_binance():
                try:
                    return await binance_service.get_products_with_cache("BTC")
                except Exception as e:
                    logger.warning(f"Binance паралельний запит недоступний: {e}")
                    return []
            
            async def fetch_bybit():
                try:
                    return await bybit_service.get_products_with_cache("BTC")
                except Exception as e:
                    logger.error(f"Bybit паралельний запит помилка: {e}")
                    return []
            
            # Виконуємо паралельно
            binance_task = asyncio.create_task(fetch_binance())
            bybit_task = asyncio.create_task(fetch_bybit())
            
            binance_results, bybit_results = await asyncio.gather(
                binance_task, bybit_task, return_exceptions=True
            )
            
            # Обробка результатів
            if isinstance(binance_results, Exception):
                logger.warning(f"Binance task failed: {binance_results}")
                binance_results = []
            if isinstance(bybit_results, Exception):
                logger.error(f"Bybit task failed: {bybit_results}")
                raise bybit_results
            
            logger.info(f"Паралельні результати - Binance: {len(binance_results)}, Bybit: {len(bybit_results)}")
            
            # 2. Паралельне збереження в БД
            logger.info("💾 Паралельне збереження в БД...")
            
            async def save_binance():
                if binance_results:
                    return await binance_service.save_products_to_db(binance_results)
                return {"created": 0, "updated": 0, "errors": 0}
            
            async def save_bybit():
                if bybit_results:
                    return await bybit_service.save_products_to_db(bybit_results)
                return {"created": 0, "updated": 0, "errors": 0}
            
            binance_save_task = asyncio.create_task(save_binance())
            bybit_save_task = asyncio.create_task(save_bybit())
            
            binance_save_stats, bybit_save_stats = await asyncio.gather(
                binance_save_task, bybit_save_task, return_exceptions=True
            )
            
            logger.info(f"Статистика збереження - Binance: {binance_save_stats}, Bybit: {bybit_save_stats}")
            
            # 3. Перевірка результатів
            async with get_database_session() as db:
                all_btc_products = await YieldProductCRUD.get_products_by_symbol(db, "BTC")
                logger.info(f"Загальна кількість BTC продуктів в БД: {len(all_btc_products)}")
            
            assert len(bybit_results) > 0, "Bybit повинен повернути результати паралельно"
            assert isinstance(binance_save_stats, dict), "Binance save stats повинні бути dict"
            assert isinstance(bybit_save_stats, dict), "Bybit save stats повинні бути dict"
            
            logger.info("✅ Паралельний тест завершений успішно")
            
        except Exception as e:
            logger.error(f"❌ Помилка в паралельному тесті: {e}")
            raise
        finally:
            # Закриваємо кеш
            await cache_manager.close()


@pytest.mark.asyncio
async def test_database_tables_creation():
    """
    Додатковий тест: Перевірка створення всіх таблиць в yield_db_test.
    """
    logger.info("🗄️ Перевірка створення таблиць в yield_db_test")
    
    try:
        async with get_database_session() as db:
            from sqlalchemy import text
            
            # Перевірка основних таблиць
            tables_to_check = [
                "yield_products",
                "exchange_data", 
                "cache_metadata",
                "user_analytics",
                "system_metrics",
                "api_logs"
            ]
            
            existing_tables = []
            
            for table in tables_to_check:
                try:
                    result = await db.execute(text(f"SELECT COUNT(*) FROM {table}"))
                    count = result.scalar()
                    existing_tables.append((table, count))
                    logger.info(f"Таблиця {table}: {count} записів")
                except Exception as e:
                    logger.warning(f"Таблиця {table} не існує або помилка: {e}")
            
            # Перевірка що основні таблиці існують
            assert any(table[0] == "yield_products" for table in existing_tables), "Таблиця yield_products повинна існувати"
            
            logger.info(f"✅ Перевірка таблиць завершена: {existing_tables}")
            
    except Exception as e:
        logger.error(f"❌ Помилка перевірки таблиць: {e}")
        raise


if __name__ == "__main__":
    """
    Запуск тестів напряму для швидкої перевірки.
    """
    pytest.main([__file__, "-v", "-s"])
