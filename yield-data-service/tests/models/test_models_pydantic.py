import pytest
from datetime import datetime
from pydantic import ValidationError

from app.models.yield_product import (
    YieldProduct,
    YieldProductCreate,
    YieldProductUpdate,
    YieldProductFilter,
    RiskLevel,
)
from app.models.response import (
    YieldResponse,
    ErrorResponse,
    HealthResponse,
    StatsResponse,
    create_success_response,
    create_error_response,
)


class TestYieldProduct:
    def test_create_valid_product(self):
        product_data = {
            "id": "test_binance_btc_1234567890",
            "symbol": "BTC",
            "name": "Bitcoin Flexible Savings",
            "provider": "Binance",
            "apy": 5.25,
            "is_cefi": True,
            "min_amount": 0.001,
            "max_amount": 100.0,
            "lock_period_days": 0,
            "max_apy": 6.0,
            "risk_level": RiskLevel.MEDIUM,
            "is_active": True,
            "website_url": "https://www.binance.com/en/earn",
            "description": "Bitcoin Flexible Savings Product",
        }

        product = YieldProduct(**product_data)

        assert product.symbol == "BTC"
        assert product.apy == 5.25
        assert product.is_cefi is True
        assert product.risk_level == RiskLevel.MEDIUM
        assert product.is_active is True

    def test_symbol_validation_uppercase(self):
        product_data = {
            "id": "test_1",
            "symbol": "btc",
            "name": "Test Product",
            "provider": "Test",
            "apy": 5.0,
        }

        product = YieldProduct(**product_data)
        assert product.symbol == "BTC"

    def test_symbol_validation_normalizes_exchange_data(self):
        product = YieldProduct(id="test_1", symbol="btc@123", name="Test", provider="Test", apy=5)
        assert product.symbol == "BTC123"

    def test_apy_validation_valid_range(self):
        product_data = {
            "id": "test_1",
            "symbol": "BTC",
            "name": "Test Product",
            "provider": "Test",
            "apy": 15.5,
        }

        product = YieldProduct(**product_data)
        assert product.apy == 15.5

    def test_apy_validation_too_high(self):
        product_data = {
            "id": "test_1",
            "symbol": "BTC",
            "name": "Test Product",
            "provider": "Test",
            "apy": 1500.0,  # > 1000%
        }

        with pytest.raises(ValidationError) as exc_info:
            YieldProduct(**product_data)

        assert "Input should be less than or equal to 1000" in str(exc_info.value)

    def test_apy_validation_negative(self):
        product_data = {
            "id": "test_1",
            "symbol": "BTC",
            "name": "Test Product",
            "provider": "Test",
            "apy": -5.0,
        }

        with pytest.raises(ValidationError) as exc_info:
            YieldProduct(**product_data)

        assert "Input should be greater than or equal to 0" in str(exc_info.value)

    def test_min_amount_validation(self):
        product_data = {
            "id": "test_1",
            "symbol": "BTC",
            "name": "Test Product",
            "provider": "Test",
            "apy": 5.0,
            "min_amount": -1.0,
        }

        with pytest.raises(ValidationError) as exc_info:
            YieldProduct(**product_data)

        assert "Input should be greater than or equal to 0" in str(exc_info.value)

    def test_max_amount_validation(self):
        product_data = {
            "id": "test_1",
            "symbol": "BTC",
            "name": "Test Product",
            "provider": "Test",
            "apy": 5.0,
            "min_amount": 10.0,
            "max_amount": 5.0,
        }

        with pytest.raises(ValidationError) as exc_info:
            YieldProduct(**product_data)

        assert "Максимальна сума не може бути меншою за мінімальну" in str(exc_info.value)

    def test_lock_period_validation(self):
        product_data = {
            "id": "test_1",
            "symbol": "BTC",
            "name": "Test Product",
            "provider": "Test",
            "apy": 5.0,
            "lock_period_days": -5,
        }

        with pytest.raises(ValidationError) as exc_info:
            YieldProduct(**product_data)

        assert "Input should be greater than or equal to 0" in str(exc_info.value)

    def test_max_apy_is_at_least_current_apy(self):
        product = YieldProduct(
            id="test_1", symbol="BTC", name="Test", provider="Test", apy=10, max_apy=5
        )
        assert product.max_apy == product.apy

    def test_to_dict_method(self):
        product_data = {
            "id": "test_1",
            "symbol": "BTC",
            "name": "Test Product",
            "provider": "Test",
            "apy": 5.0,
        }

        product = YieldProduct(**product_data)
        product_dict = product.to_dict()

        assert isinstance(product_dict, dict)
        assert product_dict["symbol"] == "BTC"
        assert product_dict["apy"] == 5.0

    def test_from_dict_method(self):
        product_data = {
            "id": "test_1",
            "symbol": "BTC",
            "name": "Test Product",
            "provider": "Test",
            "apy": 5.0,
        }

        product = YieldProduct.from_dict(product_data)

        assert product.symbol == "BTC"
        assert product.apy == 5.0

    def test_is_flexible_method(self):

        flexible_product = YieldProduct(
            id="test_1", symbol="BTC", name="Test", provider="Test", apy=5.0, lock_period_days=0
        )
        assert flexible_product.is_flexible() is True

        locked_product = YieldProduct(
            id="test_2", symbol="BTC", name="Test", provider="Test", apy=5.0, lock_period_days=30
        )
        assert locked_product.is_flexible() is False

    def test_is_high_yield_method(self):

        high_yield_product = YieldProduct(
            id="test_1", symbol="BTC", name="Test", provider="Test", apy=15.0
        )
        assert high_yield_product.is_high_yield(threshold=10.0) is True

        low_yield_product = YieldProduct(
            id="test_2", symbol="BTC", name="Test", provider="Test", apy=5.0
        )
        assert low_yield_product.is_high_yield(threshold=10.0) is False

    def test_get_effective_apy_method(self):

        product_with_max = YieldProduct(
            id="test_1", symbol="BTC", name="Test", provider="Test", apy=5.0, max_apy=8.0
        )
        assert product_with_max.get_effective_apy() == 8.0

        product_without_max = YieldProduct(
            id="test_2", symbol="BTC", name="Test", provider="Test", apy=5.0
        )
        assert product_without_max.get_effective_apy() == 5.0


class TestYieldProductCreate:
    def test_create_valid_product(self):
        product_data = {
            "symbol": "BTC",
            "name": "Bitcoin Flexible Savings",
            "provider": "Binance",
            "apy": 5.25,
            "is_cefi": True,
            "min_amount": 0.001,
        }

        product = YieldProductCreate(**product_data)

        assert product.symbol == "BTC"
        assert product.apy == 5.25
        assert product.is_cefi is True


class TestYieldProductUpdate:
    def test_partial_update(self):
        update_data = {"apy": 6.0, "is_active": False}

        update = YieldProductUpdate(**update_data)

        assert update.apy == 6.0
        assert update.is_active is False

        assert update.name is None


class TestYieldProductFilter:
    def test_filter_creation(self):
        filter_data = {
            "symbol": "BTC",
            "provider": "Binance",
            "min_apy": 5.0,
            "max_apy": 10.0,
            "is_cefi": True,
        }

        filter_obj = YieldProductFilter(**filter_data)

        assert filter_obj.symbol == "BTC"
        assert filter_obj.provider == "Binance"
        assert filter_obj.min_apy == 5.0
        assert filter_obj.max_apy == 10.0
        assert filter_obj.is_cefi is True

    def test_to_sql_filters_method(self):
        filter_obj = YieldProductFilter(
            symbol="BTC", provider="Binance", min_apy=5.0, max_apy=10.0, is_cefi=True
        )

        sql_filters = filter_obj.to_sql_filters()

        assert sql_filters["symbol"] == "BTC"
        assert sql_filters["provider"] == "Binance"
        assert sql_filters["apy__gte"] == 5.0
        assert sql_filters["apy__lte"] == 10.0
        assert sql_filters["is_cefi"] is True


class TestResponseModels:
    def test_yield_response_creation(self):
        response = YieldResponse(success=True, data=[], count=0, cached=False, source="test")

        assert response.success is True
        assert response.count == 0
        assert response.cached is False
        assert response.source == "test"

    def test_yield_response_auto_count(self):
        from app.models.yield_product import YieldProduct

        products = [
            YieldProduct(id="1", symbol="BTC", name="Test1", provider="Test", apy=5.0),
            YieldProduct(id="2", symbol="ETH", name="Test2", provider="Test", apy=6.0),
        ]

        response = YieldResponse(success=True, data=products)

        assert response.count == 2

    def test_error_response_creation(self):
        response = ErrorResponse(error="Test Error", details="Test details")

        assert response.success is False
        assert response.error == "Test Error"
        assert response.details == "Test details"

    def test_health_response_creation(self):
        response = HealthResponse(
            service="test-service", version="1.0.0", database_status="healthy"
        )

        assert response.success is True
        assert response.service == "test-service"
        assert response.database_status == "healthy"

    def test_stats_response_creation(self):
        response = StatsResponse(
            total_products=100, active_products=95, providers_count=3, symbols_count=10, avg_apy=5.5
        )

        assert response.success is True
        assert response.total_products == 100
        assert response.avg_apy == 5.5


class TestUtilityFunctions:
    def test_create_success_response(self):
        from app.models.yield_product import YieldProduct

        products = [YieldProduct(id="1", symbol="BTC", name="Test1", provider="Test", apy=5.0)]

        response = create_success_response(
            data=products, message="Test message", cached=True, source="test"
        )

        assert response.success is True
        assert response.count == 1
        assert response.cached is True
        assert response.source == "test"
        assert response.message == "Test message"

    def test_create_error_response(self):
        response = create_error_response(
            error="Test Error", details="Test details", error_code="TEST_001"
        )

        assert response.success is False
        assert response.error == "Test Error"
        assert response.details == "Test details"
        assert response.error_code == "TEST_001"
