"""
Тести для Response моделей.

Тестує функціональність response моделей:
- YieldResponse
- ErrorResponse  
- HealthResponse
- StatsResponse
- Утилітарні функції
"""

import pytest
from datetime import datetime
from typing import List

from app.models.yield_product import YieldProduct, RiskLevel
from app.models.response import (
    YieldResponse, ErrorResponse, HealthResponse, StatsResponse,
    WarningResponse, InfoResponse, PaginatedResponse, CacheResponse,
    create_success_response, create_error_response, create_warning_response,
    create_health_response, ResponseStatus
)


class TestYieldResponse:
    """Тести для YieldResponse моделі."""
    
    def test_basic_creation(self):
        """Тест базового створення YieldResponse."""
        response = YieldResponse(
            success=True,
            data=[],
            count=0,
            cached=False,
            source="test"
        )
        
        assert response.success is True
        assert response.data == []
        assert response.count == 0
        assert response.cached is False
        assert response.source == "test"
    
    def test_auto_count_calculation(self):
        """Тест автоматичного підрахунку count."""
        products = [
            YieldProduct(id="1", symbol="BTC", name="Test1", provider="Test", apy=5.0),
            YieldProduct(id="2", symbol="ETH", name="Test2", provider="Test", apy=6.0)
        ]
        
        response = YieldResponse(success=True, data=products)
        
        assert response.count == 2  # Автоматично підраховано
    
    def test_add_product_method(self):
        """Тест методу add_product()."""
        response = YieldResponse(success=True, data=[])
        
        product = YieldProduct(id="1", symbol="BTC", name="Test", provider="Test", apy=5.0)
        response.add_product(product)
        
        assert len(response.data) == 1
        assert response.count == 1
        assert response.data[0].symbol == "BTC"
    
    def test_add_products_method(self):
        """Тест методу add_products()."""
        response = YieldResponse(success=True, data=[])
        
        products = [
            YieldProduct(id="1", symbol="BTC", name="Test1", provider="Test", apy=5.0),
            YieldProduct(id="2", symbol="ETH", name="Test2", provider="Test", apy=6.0)
        ]
        
        response.add_products(products)
        
        assert len(response.data) == 2
        assert response.count == 2
    
    def test_get_top_products_method(self):
        """Тест методу get_top_products()."""
        products = [
            YieldProduct(id="1", symbol="BTC", name="Test1", provider="Test", apy=5.0),
            YieldProduct(id="2", symbol="ETH", name="Test2", provider="Test", apy=8.0),
            YieldProduct(id="3", symbol="USDT", name="Test3", provider="Test", apy=3.0)
        ]
        
        response = YieldResponse(success=True, data=products)
        top_products = response.get_top_products(limit=2)
        
        assert len(top_products) == 2
        assert top_products[0].apy == 8.0  # Найвищий APY
        assert top_products[1].apy == 5.0  # Другий за APY
    
    def test_get_products_by_provider_method(self):
        """Тест методу get_products_by_provider()."""
        products = [
            YieldProduct(id="1", symbol="BTC", name="Test1", provider="Binance", apy=5.0),
            YieldProduct(id="2", symbol="ETH", name="Test2", provider="Bybit", apy=6.0),
            YieldProduct(id="3", symbol="BTC", name="Test3", provider="Binance", apy=7.0)
        ]
        
        response = YieldResponse(success=True, data=products)
        binance_products = response.get_products_by_provider("Binance")
        
        assert len(binance_products) == 2
        assert all(p.provider == "Binance" for p in binance_products)
    
    def test_get_products_by_symbol_method(self):
        """Тест методу get_products_by_symbol()."""
        products = [
            YieldProduct(id="1", symbol="BTC", name="Test1", provider="Test", apy=5.0),
            YieldProduct(id="2", symbol="ETH", name="Test2", provider="Test", apy=6.0),
            YieldProduct(id="3", symbol="BTC", name="Test3", provider="Test", apy=7.0)
        ]
        
        response = YieldResponse(success=True, data=products)
        btc_products = response.get_products_by_symbol("BTC")
        
        assert len(btc_products) == 2
        assert all(p.symbol == "BTC" for p in btc_products)


class TestErrorResponse:
    """Тести для ErrorResponse моделі."""
    
    def test_basic_creation(self):
        """Тест базового створення ErrorResponse."""
        response = ErrorResponse(
            error="Test Error",
            details="Test details"
        )
        
        assert response.success is False
        assert response.error == "Test Error"
        assert response.details == "Test details"
        assert response.status == ResponseStatus.ERROR
    
    def test_with_error_code(self):
        """Тест створення з кодом помилки."""
        response = ErrorResponse(
            error="Validation Error",
            details="Invalid data",
            error_code="VAL_001",
            trace_id="trace_123"
        )
        
        assert response.error_code == "VAL_001"
        assert response.trace_id == "trace_123"


class TestHealthResponse:
    """Тести для HealthResponse моделі."""
    
    def test_basic_creation(self):
        """Тест базового створення HealthResponse."""
        response = HealthResponse(
            service="test-service",
            version="1.0.0"
        )
        
        assert response.success is True
        assert response.service == "test-service"
        assert response.version == "1.0.0"
        assert response.status == ResponseStatus.SUCCESS
    
    def test_with_database_status(self):
        """Тест з статусом бази даних."""
        response = HealthResponse(
            service="test-service",
            version="1.0.0",
            database_status="healthy",
            cache_status="healthy",
            api_status={"binance": "healthy", "bybit": "healthy"}
        )
        
        assert response.database_status == "healthy"
        assert response.cache_status == "healthy"
        assert response.api_status["binance"] == "healthy"


class TestStatsResponse:
    """Тести для StatsResponse моделі."""
    
    def test_basic_creation(self):
        """Тест базового створення StatsResponse."""
        response = StatsResponse(
            total_products=100,
            active_products=95,
            providers_count=3,
            symbols_count=10
        )
        
        assert response.success is True
        assert response.total_products == 100
        assert response.active_products == 95
        assert response.providers_count == 3
        assert response.symbols_count == 10
    
    def test_with_apy_stats(self):
        """Тест з APY статистикою."""
        response = StatsResponse(
            total_products=100,
            active_products=95,
            providers_count=3,
            symbols_count=10,
            avg_apy=5.5,
            max_apy=15.0,
            min_apy=1.0,
            cache_hit_rate=85.5
        )
        
        assert response.avg_apy == 5.5
        assert response.max_apy == 15.0
        assert response.min_apy == 1.0
        assert response.cache_hit_rate == 85.5


class TestWarningResponse:
    """Тести для WarningResponse моделі."""
    
    def test_basic_creation(self):
        """Тест базового створення WarningResponse."""
        response = WarningResponse(
            warning="Test warning",
            details="Test details"
        )
        
        assert response.success is True
        assert response.warning == "Test warning"
        assert response.details == "Test details"
        assert response.status == ResponseStatus.WARNING


class TestInfoResponse:
    """Тести для InfoResponse моделі."""
    
    def test_basic_creation(self):
        """Тест базового створення InfoResponse."""
        response = InfoResponse(
            info="Test info",
            details="Test details"
        )
        
        assert response.success is True
        assert response.info == "Test info"
        assert response.details == "Test details"
        assert response.status == ResponseStatus.INFO


class TestPaginatedResponse:
    """Тести для PaginatedResponse моделі."""
    
    def test_basic_creation(self):
        """Тест базового створення PaginatedResponse."""
        products = [
            YieldProduct(id="1", symbol="BTC", name="Test1", provider="Test", apy=5.0)
        ]
        
        response = PaginatedResponse(
            data=products,
            count=1,
            page=1,
            per_page=20
        )
        
        assert response.success is True
        assert response.count == 1
        assert response.page == 1
        assert response.per_page == 20
        assert response.total_pages == 1
        assert response.has_next is False
        assert response.has_prev is False
    
    def test_auto_pagination_calculation(self):
        """Тест автоматичного розрахунку пагінації."""
        products = [YieldProduct(id=str(i), symbol="BTC", name=f"Test{i}", provider="Test", apy=5.0) for i in range(25)]
        
        response = PaginatedResponse(
            data=products,
            count=25,
            page=1,
            per_page=10
        )
        
        assert response.total_pages == 3  # 25 / 10 = 2.5, округлено до 3
        assert response.has_next is True
        assert response.has_prev is False


class TestCacheResponse:
    """Тести для CacheResponse моделі."""
    
    def test_basic_creation(self):
        """Тест базового створення CacheResponse."""
        response = CacheResponse(
            cache_key="test:key",
            hit_count=10,
            miss_count=5
        )
        
        assert response.success is True
        assert response.cache_key == "test:key"
        assert response.hit_count == 10
        assert response.miss_count == 5
        assert abs(response.hit_rate - 66.67) < 0.01  # 10 / (10 + 5) * 100
    
    def test_auto_hit_rate_calculation(self):
        """Тест автоматичного розрахунку hit rate."""
        response = CacheResponse(
            cache_key="test:key",
            hit_count=8,
            miss_count=2
        )
        
        assert response.hit_rate == 80.0  # 8 / (8 + 2) * 100


class TestUtilityFunctions:
    """Тести для утилітарних функцій."""
    
    def test_create_success_response(self):
        """Тест функції create_success_response()."""
        products = [
            YieldProduct(id="1", symbol="BTC", name="Test1", provider="Test", apy=5.0)
        ]
        
        response = create_success_response(
            data=products,
            message="Test message",
            cached=True,
            source="test"
        )
        
        assert response.success is True
        assert response.count == 1
        assert response.cached is True
        assert response.source == "test"
        assert response.message == "Test message"
    
    def test_create_error_response(self):
        """Тест функції create_error_response()."""
        response = create_error_response(
            error="Test Error",
            details="Test details",
            error_code="TEST_001",
            trace_id="trace_123"
        )
        
        assert response.success is False
        assert response.error == "Test Error"
        assert response.details == "Test details"
        assert response.error_code == "TEST_001"
        assert response.trace_id == "trace_123"
    
    def test_create_warning_response_with_data(self):
        """Тест функції create_warning_response() з даними."""
        products = [
            YieldProduct(id="1", symbol="BTC", name="Test1", provider="Test", apy=5.0)
        ]
        
        response = create_warning_response(
            warning="Test warning",
            details="Test details",
            data=products
        )
        
        assert response.success is True
        assert response.count == 1
        assert response.message == "Test warning"
        assert response.status == ResponseStatus.WARNING
    
    def test_create_warning_response_without_data(self):
        """Тест функції create_warning_response() без даних."""
        response = create_warning_response(
            warning="Test warning",
            details="Test details"
        )
        
        assert response.success is True
        assert response.warning == "Test warning"
        assert response.details == "Test details"
        assert response.status == ResponseStatus.WARNING
    
    def test_create_health_response(self):
        """Тест функції create_health_response()."""
        response = create_health_response(
            service="test-service",
            version="1.0.0",
            uptime=3600.0,
            database_status="healthy",
            cache_status="healthy",
            api_status={"binance": "healthy", "bybit": "healthy"}
        )
        
        assert response.success is True
        assert response.service == "test-service"
        assert response.version == "1.0.0"
        assert response.uptime == 3600.0
        assert response.database_status == "healthy"
        assert response.cache_status == "healthy"
        assert response.api_status["binance"] == "healthy"


class TestResponseSerialization:
    """Тести для серіалізації response моделей."""
    
    def test_yield_response_json_serialization(self):
        """Тест JSON серіалізації YieldResponse."""
        products = [
            YieldProduct(id="1", symbol="BTC", name="Test1", provider="Test", apy=5.0)
        ]
        
        response = YieldResponse(success=True, data=products)
        json_data = response.model_dump()
        
        assert json_data["success"] is True
        assert json_data["count"] == 1
        assert len(json_data["data"]) == 1
        assert json_data["data"][0]["symbol"] == "BTC"
    
    def test_error_response_json_serialization(self):
        """Тест JSON серіалізації ErrorResponse."""
        response = ErrorResponse(
            error="Test Error",
            details="Test details"
        )
        
        json_data = response.model_dump()
        
        assert json_data["success"] is False
        assert json_data["error"] == "Test Error"
        assert json_data["details"] == "Test details"
    
    def test_health_response_json_serialization(self):
        """Тест JSON серіалізації HealthResponse."""
        response = HealthResponse(
            service="test-service",
            version="1.0.0",
            database_status="healthy"
        )
        
        json_data = response.model_dump()
        
        assert json_data["success"] is True
        assert json_data["service"] == "test-service"
        assert json_data["database_status"] == "healthy"
