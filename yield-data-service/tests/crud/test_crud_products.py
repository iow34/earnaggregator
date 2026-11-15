import pytest
from datetime import datetime
from typing import List

from app.db.crud import YieldProductCRUD
from app.models.yield_product import (
    YieldProductCreate,
    YieldProductUpdate,
    YieldProductFilter,
    RiskLevel,
)


class TestYieldProductCRUD:
    async def test_create_product(self, test_db_session, sample_yield_product_data):

        create_data = YieldProductCreate(**sample_yield_product_data)

        created_product = await YieldProductCRUD.create_product(test_db_session, create_data)

        assert created_product.id == sample_yield_product_data["id"]
        assert created_product.symbol == sample_yield_product_data["symbol"]
        assert created_product.apy == sample_yield_product_data["apy"]
        assert created_product.is_active is True
        assert created_product.created_at is not None
        assert created_product.updated_at is not None

    async def test_get_product_by_id(self, test_db_session, sample_yield_product_data):

        create_data = YieldProductCreate(**sample_yield_product_data)
        created_product = await YieldProductCRUD.create_product(test_db_session, create_data)

        retrieved_product = await YieldProductCRUD.get_product_by_id(
            test_db_session, created_product.id
        )

        assert retrieved_product is not None
        assert retrieved_product.id == created_product.id
        assert retrieved_product.symbol == created_product.symbol

    async def test_get_product_by_id_not_found(self, test_db_session):
        retrieved_product = await YieldProductCRUD.get_product_by_id(
            test_db_session, "nonexistent_id"
        )

        assert retrieved_product is None

    async def test_get_products_by_symbol(self, test_db_session, multiple_yield_products):

        created_products = []
        for product_data in multiple_yield_products:
            create_data = YieldProductCreate(**product_data)
            product = await YieldProductCRUD.create_product(test_db_session, create_data)
            created_products.append(product)

        btc_products = await YieldProductCRUD.get_products_by_symbol(test_db_session, "BTC")

        assert len(btc_products) == 2
        assert all(p.symbol == "BTC" for p in btc_products)

        apy_values = [p.apy for p in btc_products]
        assert apy_values == sorted(apy_values, reverse=True)

    async def test_get_products_by_provider(self, test_db_session, multiple_yield_products):

        created_products = []
        for product_data in multiple_yield_products:
            create_data = YieldProductCreate(**product_data)
            product = await YieldProductCRUD.create_product(test_db_session, create_data)
            created_products.append(product)

        binance_products = await YieldProductCRUD.get_products_by_provider(
            test_db_session, "Binance"
        )

        assert len(binance_products) == 2
        assert all(p.provider == "Binance" for p in binance_products)

    async def test_get_all_products(self, test_db_session, multiple_yield_products):

        created_products = []
        for product_data in multiple_yield_products:
            create_data = YieldProductCreate(**product_data)
            product = await YieldProductCRUD.create_product(test_db_session, create_data)
            created_products.append(product)

        all_products = await YieldProductCRUD.get_all_products(test_db_session, limit=10, offset=0)

        assert len(all_products) == 4
        assert all(p.is_active for p in all_products)

        paginated_products = await YieldProductCRUD.get_all_products(
            test_db_session, limit=2, offset=0
        )
        assert len(paginated_products) == 2

    async def test_get_top_products(self, test_db_session, multiple_yield_products):

        created_products = []
        for product_data in multiple_yield_products:
            create_data = YieldProductCreate(**product_data)
            product = await YieldProductCRUD.create_product(test_db_session, create_data)
            created_products.append(product)

        top_products = await YieldProductCRUD.get_top_products(test_db_session, limit=2)

        assert len(top_products) == 2
        assert all(p.is_active for p in top_products)

        apy_values = [p.apy for p in top_products]
        assert apy_values == sorted(apy_values, reverse=True)
        assert apy_values[0] >= apy_values[1]

    async def test_filter_products(self, test_db_session, multiple_yield_products):

        created_products = []
        for product_data in multiple_yield_products:
            create_data = YieldProductCreate(**product_data)
            product = await YieldProductCRUD.create_product(test_db_session, create_data)
            created_products.append(product)

        btc_filter = YieldProductFilter(symbol="BTC")
        btc_products = await YieldProductCRUD.filter_products(test_db_session, btc_filter)
        assert len(btc_products) == 2
        assert all(p.symbol == "BTC" for p in btc_products)

        binance_filter = YieldProductFilter(provider="Binance")
        binance_products = await YieldProductCRUD.filter_products(test_db_session, binance_filter)
        assert len(binance_products) == 2
        assert all(p.provider == "Binance" for p in binance_products)

        apy_filter = YieldProductFilter(min_apy=6.0)
        high_apy_products = await YieldProductCRUD.filter_products(test_db_session, apy_filter)
        assert len(high_apy_products) == 2
        assert all(p.apy >= 6.0 for p in high_apy_products)

        combined_filter = YieldProductFilter(symbol="BTC", min_apy=5.0)
        filtered_products = await YieldProductCRUD.filter_products(test_db_session, combined_filter)
        assert len(filtered_products) == 2
        assert all(p.symbol == "BTC" and p.apy >= 5.0 for p in filtered_products)

    async def test_update_product(self, test_db_session, sample_yield_product_data):

        create_data = YieldProductCreate(**sample_yield_product_data)
        created_product = await YieldProductCRUD.create_product(test_db_session, create_data)

        update_data = YieldProductUpdate(
            apy=7.5, is_active=False, description="Updated description"
        )

        updated_product = await YieldProductCRUD.update_product(
            test_db_session, created_product.id, update_data
        )

        assert updated_product is not None
        assert updated_product.apy == 7.5
        assert updated_product.is_active is False
        assert updated_product.description == "Updated description"
        assert updated_product.updated_at > created_product.updated_at

    async def test_update_nonexistent_product(self, test_db_session):
        update_data = YieldProductUpdate(apy=7.5)
        updated_product = await YieldProductCRUD.update_product(
            test_db_session, "nonexistent_id", update_data
        )

        assert updated_product is None

    async def test_delete_product(self, test_db_session, sample_yield_product_data):

        create_data = YieldProductCreate(**sample_yield_product_data)
        created_product = await YieldProductCRUD.create_product(test_db_session, create_data)

        result = await YieldProductCRUD.delete_product(test_db_session, created_product.id)

        assert result is True

        deleted_product = await YieldProductCRUD.get_product_by_id(
            test_db_session, created_product.id
        )
        assert deleted_product is None

    async def test_delete_nonexistent_product(self, test_db_session):
        result = await YieldProductCRUD.delete_product(test_db_session, "nonexistent_id")

        assert result is False

    async def test_bulk_create_products(self, test_db_session, multiple_yield_products):

        create_data_list = [
            YieldProductCreate(**product_data) for product_data in multiple_yield_products
        ]

        created_products = await YieldProductCRUD.bulk_create_products(
            test_db_session, create_data_list
        )

        assert len(created_products) == len(multiple_yield_products)
        assert all(p.id is not None for p in created_products)
        assert all(p.symbol in ["BTC", "ETH"] for p in created_products)

    async def test_get_products_count(self, test_db_session, multiple_yield_products):

        initial_count = await YieldProductCRUD.get_products_count(test_db_session)
        assert initial_count == 0

        for product_data in multiple_yield_products:
            create_data = YieldProductCreate(**product_data)
            await YieldProductCRUD.create_product(test_db_session, create_data)

        final_count = await YieldProductCRUD.get_products_count(test_db_session)
        assert final_count == len(multiple_yield_products)


class TestYieldProductCRUDEdgeCases:
    async def test_create_product_with_minimal_data(self, test_db_session):
        minimal_data = {"symbol": "BTC", "name": "Bitcoin Test", "provider": "Test", "apy": 5.0}

        create_data = YieldProductCreate(**minimal_data)
        created_product = await YieldProductCRUD.create_product(test_db_session, create_data)

        assert created_product.symbol == "BTC"
        assert created_product.apy == 5.0
        assert created_product.is_cefi is True  # Default value
        assert created_product.is_active is True  # Default value
        assert created_product.min_amount == 0.0  # Default value
        assert created_product.lock_period_days == 0  # Default value

    async def test_filter_products_with_no_results(self, test_db_session):

        filter_obj = YieldProductFilter(symbol="NONEXISTENT")
        filtered_products = await YieldProductCRUD.filter_products(test_db_session, filter_obj)

        assert len(filtered_products) == 0

    async def test_get_top_products_with_empty_database(self, test_db_session):
        top_products = await YieldProductCRUD.get_top_products(test_db_session, limit=10)

        assert len(top_products) == 0

    async def test_pagination_with_large_offset(self, test_db_session, multiple_yield_products):

        for product_data in multiple_yield_products:
            create_data = YieldProductCreate(**product_data)
            await YieldProductCRUD.create_product(test_db_session, create_data)

        products = await YieldProductCRUD.get_all_products(test_db_session, limit=10, offset=100)

        assert len(products) == 0


class TestYieldProductCRUDPerformance:
    async def test_bulk_create_performance(self, test_db_session):
        import time

        products_data = []
        for i in range(50):
            product_data = {
                "symbol": f"TEST{i % 5}",
                "name": f"Test Product {i}",
                "provider": f"Provider{i % 3}",
                "apy": 5.0 + (i % 10),
            }
            products_data.append(YieldProductCreate(**product_data))

        start_time = time.time()
        created_products = await YieldProductCRUD.bulk_create_products(
            test_db_session, products_data
        )
        end_time = time.time()

        assert len(created_products) == 50
        assert (end_time - start_time) < 5.0

    async def test_filter_performance(self, test_db_session):
        import time

        for i in range(100):
            product_data = {
                "symbol": f"TEST{i % 10}",
                "name": f"Test Product {i}",
                "provider": f"Provider{i % 5}",
                "apy": 5.0 + (i % 20),
            }
            create_data = YieldProductCreate(**product_data)
            await YieldProductCRUD.create_product(test_db_session, create_data)

        start_time = time.time()
        filter_obj = YieldProductFilter(symbol="TEST0", min_apy=10.0)
        filtered_products = await YieldProductCRUD.filter_products(test_db_session, filter_obj)
        end_time = time.time()

        assert (end_time - start_time) < 1.0
        assert len(filtered_products) > 0
