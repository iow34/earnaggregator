import pytest
from datetime import datetime, timedelta
from typing import List

from app.db.crud import ExchangeDataCRUD, YieldProductCRUD
from app.models.yield_product import YieldProductCreate


class TestExchangeDataCRUD:
    async def test_create_exchange_data(
        self, test_db_session, sample_yield_product_data, sample_exchange_data
    ):

        product_data = YieldProductCreate(**sample_yield_product_data)
        product = await YieldProductCRUD.create_product(test_db_session, product_data)

        created_exchange = await ExchangeDataCRUD.create_exchange_data(
            test_db_session,
            product.id,
            sample_exchange_data["exchange"],
            sample_exchange_data["raw_data"],
            sample_exchange_data.get("api_endpoint"),
            sample_exchange_data.get("response_status"),
            sample_exchange_data.get("response_time_ms"),
        )

        assert created_exchange.product_id == product.id
        assert created_exchange.exchange == sample_exchange_data["exchange"]
        assert created_exchange.raw_data == sample_exchange_data["raw_data"]
        assert created_exchange.api_endpoint == sample_exchange_data.get("api_endpoint")
        assert created_exchange.response_status == sample_exchange_data.get("response_status")
        assert created_exchange.response_time_ms == sample_exchange_data.get("response_time_ms")
        assert created_exchange.request_timestamp is not None

    async def test_get_exchange_data_by_product(self, test_db_session, sample_yield_product_data):

        product_data = YieldProductCreate(**sample_yield_product_data)
        product = await YieldProductCRUD.create_product(test_db_session, product_data)

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
                150,
            )
            created_exchanges.append(exchange_data)

        retrieved_exchanges = await ExchangeDataCRUD.get_exchange_data_by_product(
            test_db_session, product.id
        )

        assert len(retrieved_exchanges) == 2
        assert all(ex.product_id == product.id for ex in retrieved_exchanges)
        assert set(ex.exchange for ex in retrieved_exchanges) == set(exchanges)

    async def test_get_exchange_data_by_exchange(self, test_db_session, multiple_yield_products):

        created_products = []
        for product_data in multiple_yield_products:
            create_data = YieldProductCreate(**product_data)
            product = await YieldProductCRUD.create_product(test_db_session, create_data)
            created_products.append(product)

        for i, product in enumerate(created_products):
            exchange = "Binance" if i % 2 == 0 else "Bybit"
            await ExchangeDataCRUD.create_exchange_data(
                test_db_session,
                product.id,
                exchange,
                {"test": f"data_{i}"},
                f"/api/{exchange.lower()}",
                200,
                150,
            )

        binance_exchanges = await ExchangeDataCRUD.get_exchange_data_by_exchange(
            test_db_session, "Binance"
        )

        assert len(binance_exchanges) == 2
        assert all(ex.exchange == "Binance" for ex in binance_exchanges)

    async def test_get_latest_exchange_data(self, test_db_session, sample_yield_product_data):

        product_data = YieldProductCreate(**sample_yield_product_data)
        product = await YieldProductCRUD.create_product(test_db_session, product_data)

        exchanges = ["Binance", "Bybit"]
        for i, exchange in enumerate(exchanges):
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
                150,
            )

        latest_exchanges = await ExchangeDataCRUD.get_latest_exchange_data(
            test_db_session, product.id
        )

        assert len(latest_exchanges) == 2

        timestamps = [ex.request_timestamp for ex in latest_exchanges]
        assert timestamps == sorted(timestamps, reverse=True)

    async def test_bulk_create_exchange_data(self, test_db_session, multiple_yield_products):

        created_products = []
        for product_data in multiple_yield_products:
            create_data = YieldProductCreate(**product_data)
            product = await YieldProductCRUD.create_product(test_db_session, create_data)
            created_products.append(product)

        exchange_data_list = []
        for i, product in enumerate(created_products):
            exchange_data = {
                "product_id": product.id,
                "exchange": "Binance" if i % 2 == 0 else "Bybit",
                "raw_data": {"test": f"bulk_data_{i}"},
                "api_endpoint": f"/api/bulk_{i}",
                "response_status": 200,
                "response_time_ms": 150 + i,
            }
            exchange_data_list.append(exchange_data)

        created_exchanges = await ExchangeDataCRUD.bulk_create_exchange_data(
            test_db_session, exchange_data_list
        )

        assert len(created_exchanges) == len(created_products)
        assert all(ex.product_id in [p.id for p in created_products] for ex in created_exchanges)

    async def test_get_exchange_data_count(self, test_db_session, sample_yield_product_data):

        initial_count = await ExchangeDataCRUD.get_exchange_data_count(test_db_session)
        assert initial_count == 0

        product_data = YieldProductCreate(**sample_yield_product_data)
        product = await YieldProductCRUD.create_product(test_db_session, product_data)

        for i in range(3):
            await ExchangeDataCRUD.create_exchange_data(
                test_db_session,
                product.id,
                f"Exchange{i}",
                {"test": f"data_{i}"},
                f"/api/exchange{i}",
                200,
                150,
            )

        final_count = await ExchangeDataCRUD.get_exchange_data_count(test_db_session)
        assert final_count == 3

    async def test_get_exchange_data_by_product_and_exchange(
        self, test_db_session, sample_yield_product_data
    ):

        product_data = YieldProductCreate(**sample_yield_product_data)
        product = await YieldProductCRUD.create_product(test_db_session, product_data)

        exchanges = ["Binance", "Bybit", "Binance"]
        for exchange in exchanges:
            await ExchangeDataCRUD.create_exchange_data(
                test_db_session,
                product.id,
                exchange,
                {"test": f"data_{exchange}"},
                f"/api/{exchange.lower()}",
                200,
                150,
            )

        binance_exchanges = await ExchangeDataCRUD.get_exchange_data_by_product_and_exchange(
            test_db_session, product.id, "Binance"
        )

        assert len(binance_exchanges) == 2
        assert all(ex.exchange == "Binance" for ex in binance_exchanges)
        assert all(ex.product_id == product.id for ex in binance_exchanges)


class TestExchangeDataCRUDEdgeCases:
    async def test_create_exchange_data_with_nonexistent_product(self, test_db_session):
        with pytest.raises(Exception):
            await ExchangeDataCRUD.create_exchange_data(
                test_db_session,
                "nonexistent_product_id",
                "Binance",
                {"test": "data"},
                "/api/test",
                200,
                150,
            )

    async def test_get_exchange_data_by_nonexistent_product(self, test_db_session):
        exchanges = await ExchangeDataCRUD.get_exchange_data_by_product(
            test_db_session, "nonexistent_product_id"
        )

        assert len(exchanges) == 0

    async def test_get_exchange_data_by_nonexistent_exchange(
        self, test_db_session, sample_yield_product_data
    ):

        product_data = YieldProductCreate(**sample_yield_product_data)
        product = await YieldProductCRUD.create_product(test_db_session, product_data)

        await ExchangeDataCRUD.create_exchange_data(
            test_db_session, product.id, "Binance", {"test": "data"}, "/api/binance", 200, 150
        )

        exchanges = await ExchangeDataCRUD.get_exchange_data_by_exchange(
            test_db_session, "NonexistentExchange"
        )

        assert len(exchanges) == 0

    async def test_create_exchange_data_with_large_json(
        self, test_db_session, sample_yield_product_data
    ):

        product_data = YieldProductCreate(**sample_yield_product_data)
        product = await YieldProductCRUD.create_product(test_db_session, product_data)

        large_json = {
            "data": [{"id": i, "value": f"test_value_{i}"} for i in range(1000)],
            "metadata": {"timestamp": datetime.utcnow().isoformat()},
            "nested": {"level1": {"level2": {"level3": {"deep_data": "test" * 100}}}},
        }

        created_exchange = await ExchangeDataCRUD.create_exchange_data(
            test_db_session, product.id, "Binance", large_json, "/api/large", 200, 150
        )

        assert created_exchange.raw_data == large_json
        assert len(str(created_exchange.raw_data)) > 10000


class TestExchangeDataCRUDPerformance:
    async def test_bulk_create_performance(self, test_db_session, multiple_yield_products):
        import time

        created_products = []
        for product_data in multiple_yield_products:
            create_data = YieldProductCreate(**product_data)
            product = await YieldProductCRUD.create_product(test_db_session, create_data)
            created_products.append(product)

        exchange_data_list = []
        for i in range(100):
            product = created_products[i % len(created_products)]
            exchange_data = {
                "product_id": product.id,
                "exchange": f"Exchange{i % 5}",
                "raw_data": {"test": f"bulk_data_{i}", "index": i},
                "api_endpoint": f"/api/bulk_{i}",
                "response_status": 200,
                "response_time_ms": 150 + (i % 50),
            }
            exchange_data_list.append(exchange_data)

        start_time = time.time()
        created_exchanges = await ExchangeDataCRUD.bulk_create_exchange_data(
            test_db_session, exchange_data_list
        )
        end_time = time.time()

        assert len(created_exchanges) == 100
        assert (end_time - start_time) < 5.0

    async def test_get_latest_performance(self, test_db_session, sample_yield_product_data):
        import time

        product_data = YieldProductCreate(**sample_yield_product_data)
        product = await YieldProductCRUD.create_product(test_db_session, product_data)

        for i in range(50):
            await ExchangeDataCRUD.create_exchange_data(
                test_db_session,
                product.id,
                f"Exchange{i % 3}",
                {"test": f"data_{i}"},
                f"/api/exchange{i % 3}",
                200,
                150,
            )

        start_time = time.time()
        latest_exchanges = await ExchangeDataCRUD.get_latest_exchange_data(
            test_db_session, product.id
        )
        end_time = time.time()

        assert (end_time - start_time) < 1.0
        assert len(latest_exchanges) == 3
