"""
Тести для CRUD операцій з Exchange даними.

Тестує всі CRUD операції для ExchangeDataCRUD:
- Створення exchange data
- Отримання по product_id
- Отримання по exchange
- Отримання останніх записів
- Збереження raw_data (JSON)
"""

import pytest
from datetime import datetime, timedelta
from typing import List

from app.db.crud import ExchangeDataCRUD, YieldProductCRUD
from app.models.yield_product import YieldProductCreate


class TestExchangeDataCRUD:
    """Тести для ExchangeDataCRUD."""
    
    async def test_create_exchange_data(self, test_db_session, sample_yield_product_data, sample_exchange_data):
        """Тест створення exchange data."""
        # Спочатку створюємо продукт
        product_data = YieldProductCreate(**sample_yield_product_data)
        product = await YieldProductCRUD.create_product(test_db_session, product_data)
        
        # Створюємо exchange data
        created_exchange = await ExchangeDataCRUD.create_exchange_data(
            test_db_session,
            product.id,
            sample_exchange_data["exchange"],
            sample_exchange_data["raw_data"],
            sample_exchange_data.get("api_endpoint"),
            sample_exchange_data.get("response_status"),
            sample_exchange_data.get("response_time_ms")
        )
        
        assert created_exchange.product_id == product.id
        assert created_exchange.exchange == sample_exchange_data["exchange"]
        assert created_exchange.raw_data == sample_exchange_data["raw_data"]
        assert created_exchange.api_endpoint == sample_exchange_data.get("api_endpoint")
        assert created_exchange.response_status == sample_exchange_data.get("response_status")
        assert created_exchange.response_time_ms == sample_exchange_data.get("response_time_ms")
        assert created_exchange.request_timestamp is not None
    
    async def test_get_exchange_data_by_product(self, test_db_session, sample_yield_product_data):
        """Тест отримання exchange data по product_id."""
        # Створюємо продукт
        product_data = YieldProductCreate(**sample_yield_product_data)
        product = await YieldProductCRUD.create_product(test_db_session, product_data)
        
        # Створюємо кілька exchange data для продукту
        exchanges = ["Binance", "Bybit"]
        created_exchanges = []
        
        for exchange in exchanges:
            exchange_data = await ExchangeDataCRUD.create_exchange_data(
                test_db_session,
                product.id,
                exchange,
                {"test": f"data_{exchange}"},
                f"/api/{exchange.lower()}",
                200,
                150
            )
            created_exchanges.append(exchange_data)
        
        # Отримуємо всі exchange data для продукту
        retrieved_exchanges = await ExchangeDataCRUD.get_exchange_data_by_product(test_db_session, product.id)
        
        assert len(retrieved_exchanges) == 2
        assert all(ex.product_id == product.id for ex in retrieved_exchanges)
        assert set(ex.exchange for ex in retrieved_exchanges) == set(exchanges)
    
    async def test_get_exchange_data_by_exchange(self, test_db_session, multiple_yield_products):
        """Тест отримання exchange data по exchange."""
        # Створюємо кілька продуктів
        created_products = []
        for product_data in multiple_yield_products:
            create_data = YieldProductCreate(**product_data)
            product = await YieldProductCRUD.create_product(test_db_session, create_data)
            created_products.append(product)
        
        # Створюємо exchange data для різних бірж
        for i, product in enumerate(created_products):
            exchange = "Binance" if i % 2 == 0 else "Bybit"
            await ExchangeDataCRUD.create_exchange_data(
                test_db_session,
                product.id,
                exchange,
                {"test": f"data_{i}"},
                f"/api/{exchange.lower()}",
                200,
                150
            )
        
        # Отримуємо всі exchange data для Binance
        binance_exchanges = await ExchangeDataCRUD.get_exchange_data_by_exchange(test_db_session, "Binance")
        
        assert len(binance_exchanges) == 2  # 2 продукти з Binance
        assert all(ex.exchange == "Binance" for ex in binance_exchanges)
    
    async def test_get_latest_exchange_data(self, test_db_session, sample_yield_product_data):
        """Тест отримання останніх exchange data."""
        # Створюємо продукт
        product_data = YieldProductCreate(**sample_yield_product_data)
        product = await YieldProductCRUD.create_product(test_db_session, product_data)
        
        # Створюємо кілька exchange data з різними timestamp
        exchanges = ["Binance", "Bybit"]
        for i, exchange in enumerate(exchanges):
            # Додаємо затримку щоб timestamp були різними
            if i > 0:
                import asyncio
                await asyncio.sleep(0.1)
            
            await ExchangeDataCRUD.create_exchange_data(
                test_db_session,
                product.id,
                exchange,
                {"test": f"data_{exchange}_{i}"},
                f"/api/{exchange.lower()}",
                200,
                150
            )
        
        # Отримуємо останні exchange data
        latest_exchanges = await ExchangeDataCRUD.get_latest_exchange_data(test_db_session, product.id)
        
        assert len(latest_exchanges) == 2
        # Перевіряємо що дані відсортовані за timestamp (desc)
        timestamps = [ex.request_timestamp for ex in latest_exchanges]
        assert timestamps == sorted(timestamps, reverse=True)
    
    async def test_bulk_create_exchange_data(self, test_db_session, multiple_yield_products):
        """Тест масового створення exchange data."""
        # Створюємо кілька продуктів
        created_products = []
        for product_data in multiple_yield_products:
            create_data = YieldProductCreate(**product_data)
            product = await YieldProductCRUD.create_product(test_db_session, create_data)
            created_products.append(product)
        
        # Підготовлюємо дані для масового створення
        exchange_data_list = []
        for i, product in enumerate(created_products):
            exchange_data = {
                "product_id": product.id,
                "exchange": "Binance" if i % 2 == 0 else "Bybit",
                "raw_data": {"test": f"bulk_data_{i}"},
                "api_endpoint": f"/api/bulk_{i}",
                "response_status": 200,
                "response_time_ms": 150 + i
            }
            exchange_data_list.append(exchange_data)
        
        # Масово створюємо exchange data
        created_exchanges = await ExchangeDataCRUD.bulk_create_exchange_data(test_db_session, exchange_data_list)
        
        assert len(created_exchanges) == len(created_products)
        assert all(ex.product_id in [p.id for p in created_products] for ex in created_exchanges)
    
    async def test_get_exchange_data_count(self, test_db_session, sample_yield_product_data):
        """Тест підрахунку exchange data."""
        # Спочатку перевіряємо що БД порожня
        initial_count = await ExchangeDataCRUD.get_exchange_data_count(test_db_session)
        assert initial_count == 0
        
        # Створюємо продукт
        product_data = YieldProductCreate(**sample_yield_product_data)
        product = await YieldProductCRUD.create_product(test_db_session, product_data)
        
        # Створюємо кілька exchange data
        for i in range(3):
            await ExchangeDataCRUD.create_exchange_data(
                test_db_session,
                product.id,
                f"Exchange{i}",
                {"test": f"data_{i}"},
                f"/api/exchange{i}",
                200,
                150
            )
        
        # Перевіряємо кількість
        final_count = await ExchangeDataCRUD.get_exchange_data_count(test_db_session)
        assert final_count == 3
    
    async def test_get_exchange_data_by_product_and_exchange(self, test_db_session, sample_yield_product_data):
        """Тест отримання exchange data по product_id та exchange."""
        # Створюємо продукт
        product_data = YieldProductCreate(**sample_yield_product_data)
        product = await YieldProductCRUD.create_product(test_db_session, product_data)
        
        # Створюємо exchange data для різних бірж
        exchanges = ["Binance", "Bybit", "Binance"]  # Два Binance записи
        for exchange in exchanges:
            await ExchangeDataCRUD.create_exchange_data(
                test_db_session,
                product.id,
                exchange,
                {"test": f"data_{exchange}"},
                f"/api/{exchange.lower()}",
                200,
                150
            )
        
        # Отримуємо тільки Binance exchange data
        binance_exchanges = await ExchangeDataCRUD.get_exchange_data_by_product_and_exchange(
            test_db_session, product.id, "Binance"
        )
        
        assert len(binance_exchanges) == 2  # 2 Binance записи
        assert all(ex.exchange == "Binance" for ex in binance_exchanges)
        assert all(ex.product_id == product.id for ex in binance_exchanges)


class TestExchangeDataCRUDEdgeCases:
    """Тести для крайових випадків ExchangeDataCRUD."""
    
    async def test_create_exchange_data_with_nonexistent_product(self, test_db_session):
        """Тест створення exchange data з неіснуючим product_id."""
        with pytest.raises(Exception):  # Має викинути foreign key constraint error
            await ExchangeDataCRUD.create_exchange_data(
                test_db_session,
                "nonexistent_product_id",
                "Binance",
                {"test": "data"},
                "/api/test",
                200,
                150
            )
    
    async def test_get_exchange_data_by_nonexistent_product(self, test_db_session):
        """Тест отримання exchange data по неіснуючому product_id."""
        exchanges = await ExchangeDataCRUD.get_exchange_data_by_product(test_db_session, "nonexistent_product_id")
        
        assert len(exchanges) == 0
    
    async def test_get_exchange_data_by_nonexistent_exchange(self, test_db_session, sample_yield_product_data):
        """Тест отримання exchange data по неіснуючому exchange."""
        # Створюємо продукт
        product_data = YieldProductCreate(**sample_yield_product_data)
        product = await YieldProductCRUD.create_product(test_db_session, product_data)
        
        # Створюємо exchange data
        await ExchangeDataCRUD.create_exchange_data(
            test_db_session,
            product.id,
            "Binance",
            {"test": "data"},
            "/api/binance",
            200,
            150
        )
        
        # Отримуємо exchange data по неіснуючому exchange
        exchanges = await ExchangeDataCRUD.get_exchange_data_by_exchange(test_db_session, "NonexistentExchange")
        
        assert len(exchanges) == 0
    
    async def test_create_exchange_data_with_large_json(self, test_db_session, sample_yield_product_data):
        """Тест створення exchange data з великим JSON."""
        # Створюємо продукт
        product_data = YieldProductCreate(**sample_yield_product_data)
        product = await YieldProductCRUD.create_product(test_db_session, product_data)
        
        # Створюємо великий JSON
        large_json = {
            "data": [{"id": i, "value": f"test_value_{i}"} for i in range(1000)],
            "metadata": {"timestamp": datetime.utcnow().isoformat()},
            "nested": {
                "level1": {
                    "level2": {
                        "level3": {"deep_data": "test" * 100}
                    }
                }
            }
        }
        
        # Створюємо exchange data з великим JSON
        created_exchange = await ExchangeDataCRUD.create_exchange_data(
            test_db_session,
            product.id,
            "Binance",
            large_json,
            "/api/large",
            200,
            150
        )
        
        assert created_exchange.raw_data == large_json
        assert len(str(created_exchange.raw_data)) > 10000  # Перевіряємо що JSON великий


class TestExchangeDataCRUDPerformance:
    """Тести для продуктивності ExchangeDataCRUD."""
    
    async def test_bulk_create_performance(self, test_db_session, multiple_yield_products):
        """Тест продуктивності масового створення exchange data."""
        import time
        
        # Створюємо продукти
        created_products = []
        for product_data in multiple_yield_products:
            create_data = YieldProductCreate(**product_data)
            product = await YieldProductCRUD.create_product(test_db_session, create_data)
            created_products.append(product)
        
        # Підготовлюємо багато exchange data
        exchange_data_list = []
        for i in range(100):
            product = created_products[i % len(created_products)]
            exchange_data = {
                "product_id": product.id,
                "exchange": f"Exchange{i % 5}",  # 5 різних бірж
                "raw_data": {"test": f"bulk_data_{i}", "index": i},
                "api_endpoint": f"/api/bulk_{i}",
                "response_status": 200,
                "response_time_ms": 150 + (i % 50)
            }
            exchange_data_list.append(exchange_data)
        
        start_time = time.time()
        created_exchanges = await ExchangeDataCRUD.bulk_create_exchange_data(test_db_session, exchange_data_list)
        end_time = time.time()
        
        assert len(created_exchanges) == 100
        assert (end_time - start_time) < 5.0  # Має зайняти менше 5 секунд
    
    async def test_get_latest_performance(self, test_db_session, sample_yield_product_data):
        """Тест продуктивності отримання останніх exchange data."""
        import time
        
        # Створюємо продукт
        product_data = YieldProductCreate(**sample_yield_product_data)
        product = await YieldProductCRUD.create_product(test_db_session, product_data)
        
        # Створюємо багато exchange data
        for i in range(50):
            await ExchangeDataCRUD.create_exchange_data(
                test_db_session,
                product.id,
                f"Exchange{i % 3}",  # 3 різних біржі
                {"test": f"data_{i}"},
                f"/api/exchange{i % 3}",
                200,
                150
            )
        
        # Тестуємо отримання останніх даних
        start_time = time.time()
        latest_exchanges = await ExchangeDataCRUD.get_latest_exchange_data(test_db_session, product.id)
        end_time = time.time()
        
        assert (end_time - start_time) < 1.0  # Має зайняти менше 1 секунди
        assert len(latest_exchanges) == 3  # 3 останні записи по біржах
