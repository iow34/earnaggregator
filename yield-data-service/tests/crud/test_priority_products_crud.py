"""
Тести для CRUD операцій з Priority продуктами.
"""

import pytest
from datetime import datetime, UTC

from app.db.crud import PriorityProductCRUD
from app.db.models import PriorityProductDB


class TestPriorityProductCRUD:
    """Тести для PriorityProductCRUD."""
    
    async def test_get_priority_products_by_exchange(self, test_db_session):
        """Тест отримання priority продуктів для біржі."""
        # Створюємо тестові дані
        exchange = "binance"
        symbols = ["BTC", "ETH", "SOL", "USDT"]
        
        for symbol in symbols:
            await PriorityProductCRUD.upsert_priority_product(
                db=test_db_session,
                exchange=exchange,
                symbol=symbol,
                apy=5.0 if symbol == "BTC" else 4.0,
                is_active=True,
                product_id=f"test_{symbol}",
                lock_period_days=0
            )
        
        # Отримуємо продукти
        products = await PriorityProductCRUD.get_priority_products_by_exchange(
            test_db_session, exchange
        )
        
        # Перевіряємо що отримано 4 продукти
        assert len(products) == 4
        
        # Перевіряємо порядок: BTC, ETH, SOL, USDT
        assert products[0].symbol == "BTC"
        assert products[1].symbol == "ETH"
        assert products[2].symbol == "SOL"
        assert products[3].symbol == "USDT"
    
    async def test_get_priority_products_missing_symbols(self, test_db_session):
        """Тест отримання priority продуктів з відсутніми символами."""
        exchange = "binance"
        
        # Створюємо тільки BTC та ETH
        await PriorityProductCRUD.upsert_priority_product(
            db=test_db_session,
            exchange=exchange,
            symbol="BTC",
            apy=5.0,
            is_active=True
        )
        await PriorityProductCRUD.upsert_priority_product(
            db=test_db_session,
            exchange=exchange,
            symbol="ETH",
            apy=4.0,
            is_active=True
        )
        
        # Отримуємо продукти
        products = await PriorityProductCRUD.get_priority_products_by_exchange(
            test_db_session, exchange
        )
        
        # Перевіряємо що отримано 4 продукти (2 реальні + 2 з APY=0.0)
        assert len(products) == 4
        assert products[0].symbol == "BTC"
        assert products[0].apy == 5.0
        assert products[1].symbol == "ETH"
        assert products[1].apy == 4.0
        assert products[2].symbol == "SOL"
        assert products[2].apy == 0.0
        assert products[2].is_active is False
        assert products[3].symbol == "USDT"
        assert products[3].apy == 0.0
        assert products[3].is_active is False
    
    async def test_upsert_priority_product_create(self, test_db_session):
        """Тест створення нового priority продукту."""
        product = await PriorityProductCRUD.upsert_priority_product(
            db=test_db_session,
            exchange="binance",
            symbol="BTC",
            apy=5.5,
            is_active=True,
            product_id="test_btc",
            lock_period_days=0
        )
        
        assert product.exchange == "binance"
        assert product.symbol == "BTC"
        assert product.apy == 5.5
        assert product.is_active is True
        assert product.product_id == "test_btc"
        assert product.lock_period_days == 0
        assert product.id is not None
    
    async def test_upsert_priority_product_update(self, test_db_session):
        """Тест оновлення існуючого priority продукту."""
        # Створюємо продукт
        created = await PriorityProductCRUD.upsert_priority_product(
            db=test_db_session,
            exchange="binance",
            symbol="BTC",
            apy=5.0,
            is_active=True
        )
        
        original_id = created.id
        
        # Оновлюємо продукт
        updated = await PriorityProductCRUD.upsert_priority_product(
            db=test_db_session,
            exchange="binance",
            symbol="BTC",
            apy=6.0,
            is_active=False,
            product_id="updated_btc"
        )
        
        # Перевіряємо що це той самий запис
        assert updated.id == original_id
        assert updated.apy == 6.0
        assert updated.is_active is False
        assert updated.product_id == "updated_btc"
    
    async def test_get_all_priority_products(self, test_db_session):
        """Тест отримання всіх priority продуктів."""
        # Створюємо продукти для різних бірж
        exchanges = ["binance", "bybit"]
        symbols = ["BTC", "ETH"]
        
        for exchange in exchanges:
            for symbol in symbols:
                await PriorityProductCRUD.upsert_priority_product(
                    db=test_db_session,
                    exchange=exchange,
                    symbol=symbol,
                    apy=5.0,
                    is_active=True
                )
        
        # Отримуємо всі продукти
        all_products = await PriorityProductCRUD.get_all_priority_products(test_db_session)
        
        # Перевіряємо що отримано 4 продукти (2 біржі * 2 символи)
        assert len(all_products) == 4

