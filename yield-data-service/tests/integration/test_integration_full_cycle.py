"""
Інтеграційні тести повного циклу роботи системи.

Тестує повний цикл від створення даних до їх отримання через API.
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from typing import List

from app.db.models import YieldProductDB, ExchangeDataDB, CacheMetadataDB
from app.db.crud import YieldProductCRUD, ExchangeDataCRUD, CacheMetadataCRUD
from app.models.yield_product import YieldProduct, RiskLevel


@pytest.mark.asyncio
class TestFullCycleIntegration:
    """Тести повного циклу роботи системи."""
    
    async def test_create_products_and_exchange_data(self, test_db_session):
        """Тест створення продуктів та exchange data."""
        async with test_db_session as session:
            
            # 1. Створюємо тестові продукти
            products_data = [
                {
                    "id": "BTC_BINANCE_001",
                    "symbol": "BTC",
                    "name": "Bitcoin",
                    "provider": "Binance",
                    "apy": 5.5,
                    "is_cefi": True,
                    "min_amount": 0.001,
                    "max_amount": 10.0,
                    "lock_period_days": 30,
                    "risk_level": "Medium",
                    "is_active": True
                },
                {
                    "id": "ETH_BYBIT_001", 
                    "symbol": "ETH",
                    "name": "Ethereum",
                    "provider": "Bybit",
                    "apy": 4.2,
                    "is_cefi": True,
                    "min_amount": 0.01,
                    "max_amount": 50.0,
                    "lock_period_days": 15,
                    "risk_level": "Low",
                    "is_active": True
                }
            ]
            
            created_products = []
            for product_data in products_data:
                product = YieldProductDB(**product_data)
                created_product = await crud.create_yield_product(session, product)
                created_products.append(created_product)
                assert created_product is not None, f"Продукт {product_data['id']} має бути створений"
                assert created_product.id == product_data['id']
            
            # 2. Створюємо exchange data для продуктів
            exchange_data_list = []
            for product in created_products:
                exchange_data = ExchangeDataDB(
                    product_id=product.id,
                    exchange=product.provider,
                    raw_data={
                        "api_response": f"Mock data for {product.symbol}",
                        "timestamp": datetime.utcnow().isoformat(),
                        "source": "test"
                    },
                    request_timestamp=datetime.utcnow()
                )
                created_exchange_data = await crud.create_exchange_data(session, exchange_data)
                exchange_data_list.append(created_exchange_data)
                assert created_exchange_data is not None, f"Exchange data для {product.id} має бути створене"
            
            # 3. Перевіряємо що дані збережені
            assert len(created_products) == 2, "Має бути створено 2 продукти"
            assert len(exchange_data_list) == 2, "Має бути створено 2 exchange data записів"
            
            return created_products, exchange_data_list
    
    async def test_query_products_by_symbol(self, test_db_session):
        """Тест запиту продуктів по символу."""
        async with test_db_session as session:
            # Спочатку створимо тестові дані
            await self.test_create_products_and_exchange_data(session)
            
            
            # Отримуємо продукти BTC
            btc_products = await crud.get_yield_products_by_symbol(session, "BTC")
            assert len(btc_products) >= 1, "Має бути хоча б один BTC продукт"
            
            # Перевіряємо дані
            btc_product = btc_products[0]
            assert btc_product.symbol == "BTC"
            assert btc_product.apy == 5.5
            assert btc_product.provider == "Binance"
            
            # Отримуємо продукти ETH
            eth_products = await crud.get_yield_products_by_symbol(session, "ETH")
            assert len(eth_products) >= 1, "Має бути хоча б один ETH продукт"
            
            eth_product = eth_products[0]
            assert eth_product.symbol == "ETH"
            assert eth_product.apy == 4.2
            assert eth_product.provider == "Bybit"
    
    async def test_get_top_products_by_apy(self, test_db_session):
        """Тест отримання топ продуктів за APY."""
        async with test_db_session as session:
            # Створюємо тестові дані
            await self.test_create_products_and_exchange_data(session)
            
            
            # Отримуємо топ продуктів
            top_products = await crud.get_all_yield_products(session, limit=10)
            assert len(top_products) >= 2, "Має бути хоча б 2 продукти"
            
            # Перевіряємо що продукти відсортовані за APY (найвищий спочатку)
            if len(top_products) > 1:
                for i in range(len(top_products) - 1):
                    # APY має бути в порядку спадання
                    assert top_products[i].apy >= top_products[i + 1].apy, \
                        f"Продукти мають бути відсортовані за APY: {top_products[i].apy} >= {top_products[i + 1].apy}"
    
    async def test_update_product_and_verify_change(self, test_db_session):
        """Тест оновлення продукту та перевірки змін."""
        async with test_db_session as session:
            # Створюємо тестовий продукт
            products, _ = await self.test_create_products_and_exchange_data(session)
            original_product = products[0]
            original_apy = original_product.apy
            
            
            # Оновлюємо APY
            new_apy = 6.8
            update_data = {"apy": new_apy}
            updated_product = await crud.update_yield_product(session, original_product.id, update_data)
            
            assert updated_product is not None, "Продукт має бути оновлений"
            assert updated_product.apy == new_apy, f"APY має бути оновлений до {new_apy}"
            assert updated_product.apy != original_apy, "APY має відрізнятися від оригінального"
            
            # Перевіряємо що updated_at змінився
            assert updated_product.updated_at is not None, "updated_at має бути встановлений"
            assert updated_product.updated_at > original_product.created_at, "updated_at має бути пізніше created_at"
    
    async def test_delete_product_and_cascade(self, test_db_session):
        """Тест видалення продукту та cascade delete."""
        async with test_db_session as session:
            # Створюємо тестові дані
            products, exchange_data_list = await self.test_create_products_and_exchange_data(session)
            product_to_delete = products[0]
            
            
            # Перевіряємо що exchange data існує
            initial_exchange_data = await crud.get_exchange_data_for_product(session, product_to_delete.id)
            assert len(initial_exchange_data) > 0, "Має бути exchange data для продукту"
            
            # Видаляємо продукт
            deleted = await crud.delete_yield_product(session, product_to_delete.id)
            assert deleted, "Продукт має бути видалений"
            
            # Перевіряємо що продукт видалений
            deleted_product = await crud.get_yield_product_by_id(session, product_to_delete.id)
            assert deleted_product is None, "Продукт має бути видалений з БД"
            
            # Перевіряємо cascade delete (exchange data також має бути видалено)
            remaining_exchange_data = await crud.get_exchange_data_for_product(session, product_to_delete.id)
            assert len(remaining_exchange_data) == 0, "Exchange data має бути видалено через cascade delete"
    
    async def test_cache_metadata_operations(self, test_db_session):
        """Тест операцій з cache metadata."""
        async with test_db_session as session:
            
            # Створюємо cache metadata
            cache_key = "test:btc:yields"
            cache_metadata = CacheMetadataDB(
                cache_key=cache_key,
                cache_type="yield_data",
                expires_at=datetime.utcnow() + timedelta(hours=1),
                last_accessed=datetime.utcnow()
            )
            
            created_cache = await crud.create_cache_metadata(session, cache_metadata)
            assert created_cache is not None, "Cache metadata має бути створений"
            assert created_cache.cache_key == cache_key
            
            # Отримуємо cache metadata
            retrieved_cache = await crud.get_cache_metadata(session, cache_key)
            assert retrieved_cache is not None, "Cache metadata має бути знайдений"
            assert retrieved_cache.cache_key == cache_key
            
            # Оновлюємо last_accessed
            new_access_time = datetime.utcnow()
            update_data = {"last_accessed": new_access_time}
            updated_cache = await crud.update_cache_metadata(session, cache_key, update_data)
            assert updated_cache is not None, "Cache metadata має бути оновлений"
            assert updated_cache.last_accessed == new_access_time
    
    async def test_statistics_and_analytics(self, test_db_session):
        """Тест отримання статистики та аналітики."""
        async with test_db_session as session:
            # Створюємо тестові дані
            await self.test_create_products_and_exchange_data(session)
            
            
            # Отримуємо загальну статистику
            all_products = await crud.get_all_yield_products(session)
            assert len(all_products) >= 2, "Має бути хоча б 2 продукти"
            
            # Отримуємо продукти по провайдерах
            binance_products = [p for p in all_products if p.provider == "Binance"]
            bybit_products = [p for p in all_products if p.provider == "Bybit"]
            
            assert len(binance_products) >= 1, "Має бути хоча б один Binance продукт"
            assert len(bybit_products) >= 1, "Має бути хоча б один Bybit продукт"
            
            # Перевіряємо статистику APY
            apy_values = [p.apy for p in all_products]
            max_apy = max(apy_values)
            min_apy = min(apy_values)
            
            assert max_apy >= 5.5, f"Максимальний APY має бути >= 5.5, отримано {max_apy}"
            assert min_apy <= 4.2, f"Мінімальний APY має бути <= 4.2, отримано {min_apy}"
            
            # Перевіряємо активні продукти
            active_products = [p for p in all_products if p.is_active]
            assert len(active_products) == len(all_products), "Всі тестові продукти мають бути активними"
    
    async def test_full_cycle_complete_workflow(self, test_db_session):
        """Повний тест циклу роботи системи."""
        async with test_db_session as session:
            
            print("\n🔄 Запуск повного циклу тестування...")
            
            # 1. Створення даних
            print("1️⃣ Створення тестових продуктів...")
            products, exchange_data = await self.test_create_products_and_exchange_data(session)
            
            # 2. Читання даних
            print("2️⃣ Тестування запитів по символу...")
            await self.test_query_products_by_symbol(session)
            
            # 3. Сортування та топ
            print("3️⃣ Тестування топ продуктів...")
            await self.test_get_top_products_by_apy(session)
            
            # 4. Оновлення
            print("4️⃣ Тестування оновлення...")
            await self.test_update_product_and_verify_change(session)
            
            # 5. Кеш операції
            print("5️⃣ Тестування кеш операцій...")
            await self.test_cache_metadata_operations(session)
            
            # 6. Статистика
            print("6️⃣ Тестування статистики...")
            await self.test_statistics_and_analytics(session)
            
            # 7. Видалення (очищення)
            print("7️⃣ Очищення тестових даних...")
            for product in products:
                await crud.delete_yield_product(session, product.id)
            
            print("✅ Повний цикл тестування завершено успішно!")
            
            # Фінальна перевірка - дані мають бути видалені
            remaining_products = await crud.get_all_yield_products(session)
            assert len(remaining_products) == 0, "Всі тестові дані мають бути видалені"
