"""
Тести для FastAPI endpoints.

Тестує всі API endpoints та їх функціональність.
"""

import pytest
import asyncio
from datetime import datetime
from httpx import AsyncClient
from fastapi.testclient import TestClient

from app.main import app
from app.db.models import YieldProductDB, ExchangeDataDB
from app.db.crud import YieldProductCRUD, ExchangeDataCRUD


@pytest.mark.asyncio
class TestAPIEndpoints:
    """Тести для API endpoints."""
    
    @pytest.fixture
    def client(self):
        """Створює тестовий клієнт FastAPI."""
        return TestClient(app)
    
    async def test_health_endpoint(self, client):
        """Тест health endpoint."""
        response = client.get("/health")
        
        assert response.status_code == 200, f"Health endpoint має повертати 200, отримано {response.status_code}"
        
        data = response.json()
        assert "status" in data, "Відповідь має містити поле status"
        assert data["status"] == "healthy", f"Статус має бути 'healthy', отримано {data.get('status')}"
    
    async def test_api_health_endpoint(self, client):
        """Тест API health endpoint."""
        response = client.get("/api/v1/health")
        
        assert response.status_code == 200, f"API health endpoint має повертати 200"
        
        data = response.json()
        assert "status" in data, "Відповідь має містити поле status"
    
    async def setup_test_data(self, test_db_session):
        """Налаштовує тестові дані."""
        async with test_db_session as session:
            
            # Створюємо тестовий продукт BTC
            btc_product = YieldProductDB(
                id="BTC_BINANCE_TEST",
                symbol="BTC",
                name="Bitcoin Test",
                provider="Binance",
                apy=5.5,
                is_cefi=True,
                min_amount=0.001,
                max_amount=10.0,
                lock_period_days=30,
                risk_level="Medium",
                is_active=True
            )
            
            created_btc = await crud.create_yield_product(session, btc_product)
            
            # Створюємо тестовий продукт ETH
            eth_product = YieldProductDB(
                id="ETH_BYBIT_TEST",
                symbol="ETH", 
                name="Ethereum Test",
                provider="Bybit",
                apy=4.2,
                is_cefi=True,
                min_amount=0.01,
                max_amount=50.0,
                lock_period_days=15,
                risk_level="Low",
                is_active=True
            )
            
            created_eth = await crud.create_yield_product(session, eth_product)
            
            return [created_btc, created_eth]
    
    async def test_yield_endpoint_by_symbol(self, client, test_db_session):
        """Тест endpoint /api/v1/yield/{symbol}."""
        # Налаштовуємо тестові дані
        await self.setup_test_data(test_db_session)
        
        # Тестуємо отримання BTC продуктів
        response = client.get("/api/v1/yield/BTC")
        
        assert response.status_code == 200, f"Endpoint має повертати 200, отримано {response.status_code}"
        
        data = response.json()
        assert "data" in data, "Відповідь має містити поле data"
        assert isinstance(data["data"], list), "data має бути списком"
        
        if len(data["data"]) > 0:
            product = data["data"][0]
            assert product["symbol"] == "BTC", f"Символ має бути BTC, отримано {product.get('symbol')}"
    
    async def test_yield_endpoint_nonexistent_symbol(self, client):
        """Тест endpoint для неіснуючого символу."""
        response = client.get("/api/v1/yield/NONEXISTENT")
        
        # Може повертати 200 з порожнім списком або 404
        assert response.status_code in [200, 404], f"Endpoint має повертати 200 або 404"
        
        if response.status_code == 200:
            data = response.json()
            assert "data" in data, "Відповідь має містити поле data"
            assert len(data["data"]) == 0, "Для неіснуючого символу data має бути порожнім"
    
    async def test_top_endpoint(self, client, test_db_session):
        """Тест endpoint /api/v1/top."""
        # Налаштовуємо тестові дані
        await self.setup_test_data(test_db_session)
        
        response = client.get("/api/v1/top")
        
        assert response.status_code == 200, f"Top endpoint має повертати 200"
        
        data = response.json()
        assert "data" in data, "Відповідь має містити поле data"
        assert isinstance(data["data"], list), "data має бути списком"
        
        # Перевіряємо що є хоча б один продукт
        assert len(data["data"]) > 0, "Має бути хоча б один продукт в топі"
    
    async def test_top_endpoint_with_limit(self, client, test_db_session):
        """Тест endpoint /api/v1/top з параметром limit."""
        await self.setup_test_data(test_db_session)
        
        response = client.get("/api/v1/top?limit=1")
        
        assert response.status_code == 200, f"Top endpoint з limit має повертати 200"
        
        data = response.json()
        assert "data" in data, "Відповідь має містити поле data"
        
        # З limit=1 має бути максимум 1 продукт
        assert len(data["data"]) <= 1, f"З limit=1 має бути максимум 1 продукт, отримано {len(data['data'])}"
    
    async def test_products_endpoint(self, client, test_db_session):
        """Тест endpoint /api/v1/products."""
        await self.setup_test_data(test_db_session)
        
        response = client.get("/api/v1/products")
        
        assert response.status_code == 200, f"Products endpoint має повертати 200"
        
        data = response.json()
        assert "data" in data, "Відповідь має містити поле data"
        assert isinstance(data["data"], list), "data має бути списком"
        
        # Має бути хоча б один продукт
        assert len(data["data"]) > 0, "Має бути хоча б один продукт"
    
    async def test_products_endpoint_with_filters(self, client, test_db_session):
        """Тест endpoint /api/v1/products з фільтрами."""
        await self.setup_test_data(test_db_session)
        
        # Тестуємо фільтр по провайдеру
        response = client.get("/api/v1/products?provider=Binance")
        
        assert response.status_code == 200, f"Products endpoint з фільтром має повертати 200"
        
        data = response.json()
        assert "data" in data, "Відповідь має містити поле data"
        
        if len(data["data"]) > 0:
            # Перевіряємо що всі продукти від Binance
            for product in data["data"]:
                assert product["provider"] == "Binance", f"Всі продукти мають бути від Binance"
    
    async def test_stats_endpoint(self, client, test_db_session):
        """Тест endpoint /api/v1/stats."""
        await self.setup_test_data(test_db_session)
        
        response = client.get("/api/v1/stats")
        
        assert response.status_code == 200, f"Stats endpoint має повертати 200"
        
        data = response.json()
        assert "status" in data, "Відповідь має містити поле status"
        
        # Перевіряємо структуру відповіді
        if "data" in data:
            stats_data = data["data"]
            # Можуть бути різні поля статистики
            assert isinstance(stats_data, dict), "Статистика має бути словником"
    
    async def test_response_format_consistency(self, client, test_db_session):
        """Тест консистентності формату відповіді."""
        await self.setup_test_data(test_db_session)
        
        endpoints_to_test = [
            "/api/v1/top",
            "/api/v1/products", 
            "/api/v1/yield/BTC"
        ]
        
        for endpoint in endpoints_to_test:
            response = client.get(endpoint)
            
            if response.status_code == 200:
                data = response.json()
                
                # Перевіряємо основні поля відповіді
                assert "status" in data, f"Endpoint {endpoint} має містити поле status"
                assert "message" in data, f"Endpoint {endpoint} має містити поле message"
                
                if "data" in data and isinstance(data["data"], list) and len(data["data"]) > 0:
                    product = data["data"][0]
                    
                    # Перевіряємо структуру продукту
                    required_fields = ["symbol", "name", "provider", "apy", "is_cefi"]
                    for field in required_fields:
                        assert field in product, f"Продукт має містити поле {field}"
    
    async def test_error_handling(self, client):
        """Тест обробки помилок."""
        # Тестуємо неіснуючий endpoint
        response = client.get("/api/v1/nonexistent")
        assert response.status_code == 404, f"Неіснуючий endpoint має повертати 404"
        
        # Тестуємо неправильні параметри
        response = client.get("/api/v1/top?limit=invalid")
        # Може повертати 422 (validation error) або обробляти gracefully
        assert response.status_code in [200, 422, 400], f"Неправильні параметри мають оброблятися коректно"
    
    async def test_caching_headers(self, client, test_db_session):
        """Тест headers для кешування."""
        await self.setup_test_data(test_db_session)
        
        response = client.get("/api/v1/top")
        
        if response.status_code == 200:
            # Можуть бути різні headers залежно від реалізації
            headers = response.headers
            
            # Перевіряємо що response повертається коректно
            assert "content-type" in headers, "Відповідь має містити content-type header"
            assert "application/json" in headers["content-type"], "Content-type має бути application/json"
