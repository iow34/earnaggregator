"""
Тести для PriorityProductsService.
"""

import pytest
from app.services.priority_products_service import PriorityProductsService
from app.db.crud import YieldProductCRUD, PriorityProductCRUD
from app.models.yield_product import YieldProductCreate, RiskLevel


class TestPriorityProductsService:
    """Тести для PriorityProductsService."""
    
    async def test_update_priority_products_for_exchange(self, test_db_session):
        """Тест оновлення priority продуктів для біржі."""
        exchange = "binance"
        
        # Створюємо тестові продукти в yield_products
        test_products = [
            {
                "id": f"binance_btc_flexible",
                "symbol": "BTC",
                "name": "BTC Flexible Savings",
                "provider": "Binance",
                "apy": 5.5,
                "lock_period_days": 0,
                "is_active": True,
                "is_cefi": True,
                "min_amount": 0.001,
                "risk_level": RiskLevel.LOW
            },
            {
                "id": f"binance_eth_flexible",
                "symbol": "ETH",
                "name": "ETH Flexible Savings",
                "provider": "Binance",
                "apy": 4.8,
                "lock_period_days": 0,
                "is_active": True,
                "is_cefi": True,
                "min_amount": 0.01,
                "risk_level": RiskLevel.LOW
            }
        ]
        
        for product_data in test_products:
            create_data = YieldProductCreate(**product_data)
            await YieldProductCRUD.create_product(test_db_session, create_data)
        
        # Оновлюємо priority_products
        updated_count = await PriorityProductsService.update_priority_products_for_exchange(
            test_db_session, exchange
        )
        
        # Перевіряємо що оновлено 4 продукти (2 знайдено + 2 з APY=0.0)
        assert updated_count == 4
        
        # Перевіряємо що дані збережені правильно
        products = await PriorityProductCRUD.get_priority_products_by_exchange(
            test_db_session, exchange
        )
        
        assert len(products) == 4
        assert products[0].symbol == "BTC"
        assert products[0].apy == 5.5
        assert products[1].symbol == "ETH"
        assert products[1].apy == 4.8
        assert products[2].symbol == "SOL"
        assert products[2].apy == 0.0
        assert products[3].symbol == "USDT"
        assert products[3].apy == 0.0
    
    async def test_update_priority_products_no_products(self, test_db_session):
        """Тест оновлення priority продуктів коли немає продуктів."""
        exchange = "binance"
        
        # Оновлюємо без створення продуктів
        updated_count = await PriorityProductsService.update_priority_products_for_exchange(
            test_db_session, exchange
        )
        
        # Перевіряємо що створено 4 продукти з APY=0.0
        assert updated_count == 4
        
        products = await PriorityProductCRUD.get_priority_products_by_exchange(
            test_db_session, exchange
        )
        
        assert len(products) == 4
        assert all(p.apy == 0.0 for p in products)
        assert all(not p.is_active for p in products)
    
    async def test_update_all_exchanges(self, test_db_session):
        """Тест оновлення priority продуктів для всіх бірж."""
        # Створюємо тестові продукти для binance
        test_product = {
            "id": "binance_btc_flexible",
            "symbol": "BTC",
            "name": "BTC Flexible Savings",
            "provider": "Binance",
            "apy": 5.5,
            "lock_period_days": 0,
            "is_active": True,
            "is_cefi": True,
            "min_amount": 0.001,
            "risk_level": RiskLevel.LOW
        }
        
        create_data = YieldProductCreate(**test_product)
        await YieldProductCRUD.create_product(test_db_session, create_data)
        
        # Оновлюємо всі біржі
        stats = await PriorityProductsService.update_all_exchanges(test_db_session)
        
        # Перевіряємо що оновлено продукти для всіх бірж
        assert "total" in stats
        assert stats["total"] > 0
        assert "binance" in stats

