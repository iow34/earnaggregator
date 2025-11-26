"""
Тести для CRUD операцій з Yield продуктами.

Тестує всі CRUD операції для YieldProductCRUD:
- CREATE операції
- READ операції  
- UPDATE операції
- DELETE операції
- Bulk операції
"""

import pytest
from datetime import datetime
from typing import List

from app.db.crud import YieldProductCRUD
from app.models.yield_product import YieldProductCreate, YieldProductUpdate, YieldProductFilter, RiskLevel


class TestYieldProductCRUD:
    """Тести для YieldProductCRUD."""
    
    async def test_create_product(self, test_db_session, sample_yield_product_data):
        """Тест створення одного продукту."""
        # Конвертуємо в YieldProductCreate
        create_data = YieldProductCreate(**sample_yield_product_data)
        
        # Створюємо продукт
        created_product = await YieldProductCRUD.create_product(test_db_session, create_data)
        
        assert created_product.id == sample_yield_product_data["id"]
        assert created_product.symbol == sample_yield_product_data["symbol"]
        assert created_product.apy == sample_yield_product_data["apy"]
        assert created_product.is_active is True
        assert created_product.created_at is not None
        assert created_product.updated_at is not None
    
    async def test_get_product_by_id(self, test_db_session, sample_yield_product_data):
        """Тест отримання продукту по ID."""
        # Створюємо продукт
        create_data = YieldProductCreate(**sample_yield_product_data)
        created_product = await YieldProductCRUD.create_product(test_db_session, create_data)
        
        # Отримуємо продукт по ID
        retrieved_product = await YieldProductCRUD.get_product_by_id(test_db_session, created_product.id)
        
        assert retrieved_product is not None
        assert retrieved_product.id == created_product.id
        assert retrieved_product.symbol == created_product.symbol
    
    async def test_get_product_by_id_not_found(self, test_db_session):
        """Тест отримання неіснуючого продукту."""
        retrieved_product = await YieldProductCRUD.get_product_by_id(test_db_session, "nonexistent_id")
        
        assert retrieved_product is None
    
    async def test_get_products_by_symbol(self, test_db_session, multiple_yield_products):
        """Тест отримання продуктів по символу."""
        # Створюємо кілька продуктів
        created_products = []
        for product_data in multiple_yield_products:
            create_data = YieldProductCreate(**product_data)
            product = await YieldProductCRUD.create_product(test_db_session, create_data)
            created_products.append(product)
        
        # Отримуємо продукти по символу BTC
        btc_products = await YieldProductCRUD.get_products_by_symbol(test_db_session, "BTC")
        
        assert len(btc_products) == 2  # 2 BTC продукти
        assert all(p.symbol == "BTC" for p in btc_products)
        
        # Перевіряємо що продукти відсортовані за APY (desc)
        apy_values = [p.apy for p in btc_products]
        assert apy_values == sorted(apy_values, reverse=True)
    
    async def test_get_products_by_provider(self, test_db_session, multiple_yield_products):
        """Тест отримання продуктів по провайдеру."""
        # Створюємо кілька продуктів
        created_products = []
        for product_data in multiple_yield_products:
            create_data = YieldProductCreate(**product_data)
            product = await YieldProductCRUD.create_product(test_db_session, create_data)
            created_products.append(product)
        
        # Отримуємо продукти по провайдеру Binance
        binance_products = await YieldProductCRUD.get_products_by_provider(test_db_session, "Binance")
        
        assert len(binance_products) == 2  # 2 Binance продукти
        assert all(p.provider == "Binance" for p in binance_products)
    
    async def test_get_all_products(self, test_db_session, multiple_yield_products):
        """Тест отримання всіх продуктів з пагінацією."""
        # Створюємо кілька продуктів
        created_products = []
        for product_data in multiple_yield_products:
            create_data = YieldProductCreate(**product_data)
            product = await YieldProductCRUD.create_product(test_db_session, create_data)
            created_products.append(product)
        
        # Отримуємо всі продукти з пагінацією
        all_products = await YieldProductCRUD.get_all_products(test_db_session, limit=10, offset=0)
        
        assert len(all_products) == 4  # Всі 4 продукти
        assert all(p.is_active for p in all_products)  # Тільки активні
        
        # Перевіряємо пагінацію
        paginated_products = await YieldProductCRUD.get_all_products(test_db_session, limit=2, offset=0)
        assert len(paginated_products) == 2
    
    async def test_get_top_products(self, test_db_session, multiple_yield_products):
        """Тест отримання топ продуктів за APY."""
        # Створюємо кілька продуктів
        created_products = []
        for product_data in multiple_yield_products:
            create_data = YieldProductCreate(**product_data)
            product = await YieldProductCRUD.create_product(test_db_session, create_data)
            created_products.append(product)
        
        # Отримуємо топ 2 продукти
        top_products = await YieldProductCRUD.get_top_products(test_db_session, limit=2)
        
        assert len(top_products) == 2
        assert all(p.is_active for p in top_products)
        
        # Перевіряємо що продукти відсортовані за APY (desc)
        apy_values = [p.apy for p in top_products]
        assert apy_values == sorted(apy_values, reverse=True)
        assert apy_values[0] >= apy_values[1]  # Перший має вищий APY
    
    async def test_filter_products(self, test_db_session, multiple_yield_products):
        """Тест фільтрації продуктів."""
        # Створюємо кілька продуктів
        created_products = []
        for product_data in multiple_yield_products:
            create_data = YieldProductCreate(**product_data)
            product = await YieldProductCRUD.create_product(test_db_session, create_data)
            created_products.append(product)
        
        # Фільтр по символу
        btc_filter = YieldProductFilter(symbol="BTC")
        btc_products = await YieldProductCRUD.filter_products(test_db_session, btc_filter)
        assert len(btc_products) == 2
        assert all(p.symbol == "BTC" for p in btc_products)
        
        # Фільтр по провайдеру
        binance_filter = YieldProductFilter(provider="Binance")
        binance_products = await YieldProductCRUD.filter_products(test_db_session, binance_filter)
        assert len(binance_products) == 2
        assert all(p.provider == "Binance" for p in binance_products)
        
        # Фільтр по APY
        apy_filter = YieldProductFilter(min_apy=6.0)
        high_apy_products = await YieldProductCRUD.filter_products(test_db_session, apy_filter)
        assert len(high_apy_products) == 2
        assert all(p.apy >= 6.0 for p in high_apy_products)
        
        # Комбінований фільтр
        combined_filter = YieldProductFilter(symbol="BTC", min_apy=5.0)
        filtered_products = await YieldProductCRUD.filter_products(test_db_session, combined_filter)
        assert len(filtered_products) == 2
        assert all(p.symbol == "BTC" and p.apy >= 5.0 for p in filtered_products)
    
    async def test_update_product(self, test_db_session, sample_yield_product_data):
        """Тест оновлення продукту."""
        # Створюємо продукт
        create_data = YieldProductCreate(**sample_yield_product_data)
        created_product = await YieldProductCRUD.create_product(test_db_session, create_data)
        
        # Оновлюємо продукт
        update_data = YieldProductUpdate(
            apy=7.5,
            is_active=False,
            description="Updated description"
        )
        
        updated_product = await YieldProductCRUD.update_product(test_db_session, created_product.id, update_data)
        
        assert updated_product is not None
        assert updated_product.apy == 7.5
        assert updated_product.is_active is False
        assert updated_product.description == "Updated description"
        assert updated_product.updated_at > created_product.updated_at
    
    async def test_update_nonexistent_product(self, test_db_session):
        """Тест оновлення неіснуючого продукту."""
        update_data = YieldProductUpdate(apy=7.5)
        updated_product = await YieldProductCRUD.update_product(test_db_session, "nonexistent_id", update_data)
        
        assert updated_product is None
    
    async def test_delete_product(self, test_db_session, sample_yield_product_data):
        """Тест видалення продукту."""
        # Створюємо продукт
        create_data = YieldProductCreate(**sample_yield_product_data)
        created_product = await YieldProductCRUD.create_product(test_db_session, create_data)
        
        # Видаляємо продукт
        result = await YieldProductCRUD.delete_product(test_db_session, created_product.id)
        
        assert result is True
        
        # Перевіряємо що продукт видалено
        deleted_product = await YieldProductCRUD.get_product_by_id(test_db_session, created_product.id)
        assert deleted_product is None
    
    async def test_delete_nonexistent_product(self, test_db_session):
        """Тест видалення неіснуючого продукту."""
        result = await YieldProductCRUD.delete_product(test_db_session, "nonexistent_id")
        
        assert result is False
    
    async def test_bulk_create_products(self, test_db_session, multiple_yield_products):
        """Тест масового створення продуктів."""
        # Конвертуємо в YieldProductCreate
        create_data_list = [YieldProductCreate(**product_data) for product_data in multiple_yield_products]
        
        # Масово створюємо продукти
        created_products = await YieldProductCRUD.bulk_create_products(test_db_session, create_data_list)
        
        assert len(created_products) == len(multiple_yield_products)
        assert all(p.id is not None for p in created_products)
        assert all(p.symbol in ["BTC", "ETH"] for p in created_products)
    
    async def test_get_products_count(self, test_db_session, multiple_yield_products):
        """Тест підрахунку продуктів."""
        # Спочатку перевіряємо що БД порожня
        initial_count = await YieldProductCRUD.get_products_count(test_db_session)
        assert initial_count == 0
        
        # Створюємо кілька продуктів
        for product_data in multiple_yield_products:
            create_data = YieldProductCreate(**product_data)
            await YieldProductCRUD.create_product(test_db_session, create_data)
        
        # Перевіряємо кількість
        final_count = await YieldProductCRUD.get_products_count(test_db_session)
        assert final_count == len(multiple_yield_products)


class TestYieldProductCRUDEdgeCases:
    """Тести для крайових випадків YieldProductCRUD."""
    
    async def test_create_product_with_minimal_data(self, test_db_session):
        """Тест створення продукту з мінімальними даними."""
        minimal_data = {
            "symbol": "BTC",
            "name": "Bitcoin Test",
            "provider": "Test",
            "apy": 5.0
        }
        
        create_data = YieldProductCreate(**minimal_data)
        created_product = await YieldProductCRUD.create_product(test_db_session, create_data)
        
        assert created_product.symbol == "BTC"
        assert created_product.apy == 5.0
        assert created_product.is_cefi is True  # Default value
        assert created_product.is_active is True  # Default value
        assert created_product.min_amount == 0.0  # Default value
        assert created_product.lock_period_days == 0  # Default value
    
    async def test_filter_products_with_no_results(self, test_db_session):
        """Тест фільтрації без результатів."""
        # Фільтр по неіснуючому символу
        filter_obj = YieldProductFilter(symbol="NONEXISTENT")
        filtered_products = await YieldProductCRUD.filter_products(test_db_session, filter_obj)
        
        assert len(filtered_products) == 0
    
    async def test_get_top_products_with_empty_database(self, test_db_session):
        """Тест отримання топ продуктів з порожньої БД."""
        top_products = await YieldProductCRUD.get_top_products(test_db_session, limit=10)
        
        assert len(top_products) == 0
    
    async def test_pagination_with_large_offset(self, test_db_session, multiple_yield_products):
        """Тест пагінації з великим offset."""
        # Створюємо кілька продуктів
        for product_data in multiple_yield_products:
            create_data = YieldProductCreate(**product_data)
            await YieldProductCRUD.create_product(test_db_session, create_data)
        
        # Запитуємо з великим offset
        products = await YieldProductCRUD.get_all_products(test_db_session, limit=10, offset=100)
        
        assert len(products) == 0  # Немає продуктів на такій сторінці


class TestYieldProductCRUDPerformance:
    """Тести для продуктивності YieldProductCRUD."""
    
    async def test_bulk_create_performance(self, test_db_session):
        """Тест продуктивності масового створення."""
        import time
        
        # Створюємо багато продуктів
        products_data = []
        for i in range(50):
            product_data = {
                "symbol": f"TEST{i % 5}",  # 5 різних символів
                "name": f"Test Product {i}",
                "provider": f"Provider{i % 3}",  # 3 різних провайдери
                "apy": 5.0 + (i % 10)
            }
            products_data.append(YieldProductCreate(**product_data))
        
        start_time = time.time()
        created_products = await YieldProductCRUD.bulk_create_products(test_db_session, products_data)
        end_time = time.time()
        
        assert len(created_products) == 50
        assert (end_time - start_time) < 5.0  # Має зайняти менше 5 секунд
    
    async def test_filter_performance(self, test_db_session):
        """Тест продуктивності фільтрації."""
        import time
        
        # Створюємо багато продуктів
        for i in range(100):
            product_data = {
                "symbol": f"TEST{i % 10}",  # 10 різних символів
                "name": f"Test Product {i}",
                "provider": f"Provider{i % 5}",  # 5 різних провайдерів
                "apy": 5.0 + (i % 20)
            }
            create_data = YieldProductCreate(**product_data)
            await YieldProductCRUD.create_product(test_db_session, create_data)
        
        # Тестуємо фільтрацію
        start_time = time.time()
        filter_obj = YieldProductFilter(symbol="TEST0", min_apy=10.0)
        filtered_products = await YieldProductCRUD.filter_products(test_db_session, filter_obj)
        end_time = time.time()
        
        assert (end_time - start_time) < 1.0  # Має зайняти менше 1 секунди
        assert len(filtered_products) > 0
