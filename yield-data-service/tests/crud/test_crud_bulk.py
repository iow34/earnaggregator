import pytest
from datetime import datetime, timedelta
from typing import List

from app.db.crud import (
    YieldProductCRUD,
    ExchangeDataCRUD,
    CacheMetadataCRUD,
    bulk_upsert_products,
    bulk_create_exchange_data,
    cleanup_old_data,
    get_database_stats,
)
from app.models.yield_product import YieldProductCreate


class TestBulkUpsertProducts:
    async def test_bulk_upsert_new_products(self, test_db_session, multiple_yield_products):

        create_data_list = [
            YieldProductCreate(**product_data) for product_data in multiple_yield_products
        ]

        created_products = await bulk_upsert_products(test_db_session, create_data_list)

        assert len(created_products) == len(multiple_yield_products)
        assert all(p.id is not None for p in created_products)
        assert all(p.symbol in ["BTC", "ETH"] for p in created_products)

    async def test_bulk_upsert_existing_products(self, test_db_session, multiple_yield_products):

        create_data_list = [
            YieldProductCreate(**product_data) for product_data in multiple_yield_products
        ]
        created_products = await bulk_upsert_products(test_db_session, create_data_list)

        updated_products_data = []
        for i, product_data in enumerate(multiple_yield_products):
            updated_data = product_data.copy()
            updated_data["apy"] = product_data["apy"] + 1.0
            updated_data["description"] = f"Updated description {i}"
            updated_products_data.append(YieldProductCreate(**updated_data))

        updated_products = await bulk_upsert_products(test_db_session, updated_products_data)

        assert len(updated_products) == len(multiple_yield_products)
        assert all(
            p.apy > original_apy
            for p, original_apy in zip(
                updated_products, [pd["apy"] for pd in multiple_yield_products]
            )
        )
        assert all("Updated description" in p.description for p in updated_products)

    async def test_bulk_upsert_mixed_products(self, test_db_session, multiple_yield_products):

        first_half = multiple_yield_products[:2]
        create_data_list = [YieldProductCreate(**product_data) for product_data in first_half]
        await bulk_upsert_products(test_db_session, create_data_list)

        mixed_products_data = []

        for product_data in first_half:
            updated_data = product_data.copy()
            updated_data["apy"] = product_data["apy"] + 0.5
            mixed_products_data.append(YieldProductCreate(**updated_data))

        new_products = [
            {
                "symbol": "USDT",
                "name": "Tether Flexible Savings",
                "provider": "Binance",
                "apy": 3.5,
                "is_cefi": True,
                "min_amount": 10.0,
            },
            {
                "symbol": "SOL",
                "name": "Solana Locked Savings",
                "provider": "Bybit",
                "apy": 12.0,
                "is_cefi": True,
                "min_amount": 1.0,
                "lock_period_days": 30,
            },
        ]

        for product_data in new_products:
            mixed_products_data.append(YieldProductCreate(**product_data))

        upserted_products = await bulk_upsert_products(test_db_session, mixed_products_data)

        assert len(upserted_products) == len(mixed_products_data)

        btc_products = [p for p in upserted_products if p.symbol == "BTC"]
        assert len(btc_products) == 1
        assert btc_products[0].apy > multiple_yield_products[0]["apy"]

        usdt_products = [p for p in upserted_products if p.symbol == "USDT"]
        sol_products = [p for p in upserted_products if p.symbol == "SOL"]
        assert len(usdt_products) == 1
        assert len(sol_products) == 1


class TestBulkCreateExchangeData:
    async def test_bulk_create_exchange_data(self, test_db_session, multiple_yield_products):

        create_data_list = [
            YieldProductCreate(**product_data) for product_data in multiple_yield_products
        ]
        created_products = await bulk_upsert_products(test_db_session, create_data_list)

        exchange_data_list = []
        for i, product in enumerate(created_products):
            for j in range(2):
                exchange_data = {
                    "product_id": product.id,
                    "exchange": f"Exchange{j}",
                    "raw_data": {
                        "product_id": product.id,
                        "exchange": f"Exchange{j}",
                        "apy": product.apy + j,
                        "timestamp": datetime.utcnow().isoformat(),
                    },
                    "api_endpoint": f"/api/exchange{j}/products",
                    "response_status": 200,
                    "response_time_ms": 150 + j * 10,
                }
                exchange_data_list.append(exchange_data)

        created_exchanges = await bulk_create_exchange_data(test_db_session, exchange_data_list)

        assert len(created_exchanges) == len(exchange_data_list)
        assert all(ex.product_id in [p.id for p in created_products] for ex in created_exchanges)
        assert all(ex.exchange in ["Exchange0", "Exchange1"] for ex in created_exchanges)

    async def test_bulk_create_exchange_data_with_invalid_product_id(self, test_db_session):
        exchange_data_list = [
            {
                "product_id": "nonexistent_id_1",
                "exchange": "Binance",
                "raw_data": {"test": "data1"},
                "response_status": 200,
                "response_time_ms": 150,
            },
            {
                "product_id": "nonexistent_id_2",
                "exchange": "Bybit",
                "raw_data": {"test": "data2"},
                "response_status": 200,
                "response_time_ms": 160,
            },
        ]

        with pytest.raises(Exception):
            await bulk_create_exchange_data(test_db_session, exchange_data_list)


class TestCleanupOldData:
    async def test_cleanup_old_exchange_data(self, test_db_session, multiple_yield_products):

        create_data_list = [
            YieldProductCreate(**product_data) for product_data in multiple_yield_products
        ]
        created_products = await bulk_upsert_products(test_db_session, create_data_list)

        now = datetime.utcnow()
        exchange_data_list = []

        for i, product in enumerate(created_products):
            old_data = {
                "product_id": product.id,
                "exchange": f"OldExchange{i}",
                "raw_data": {"test": f"old_data_{i}"},
                "request_timestamp": now - timedelta(days=10),
                "response_status": 200,
                "response_time_ms": 150,
            }
            exchange_data_list.append(old_data)

            new_data = {
                "product_id": product.id,
                "exchange": f"NewExchange{i}",
                "raw_data": {"test": f"new_data_{i}"},
                "request_timestamp": now - timedelta(days=1),
                "response_status": 200,
                "response_time_ms": 150,
            }
            exchange_data_list.append(new_data)

        await bulk_create_exchange_data(test_db_session, exchange_data_list)

        cleanup_stats = await cleanup_old_data(test_db_session, days=7)

        assert cleanup_stats["exchange_data_deleted"] == len(created_products)

        remaining_exchanges = await ExchangeDataCRUD.get_exchange_data_count(test_db_session)
        assert remaining_exchanges == len(created_products)

    async def test_cleanup_old_cache_metadata(self, test_db_session):
        now = datetime.utcnow()

        cache_entries = [
            ("old_cache_1", now - timedelta(days=10)),
            ("old_cache_2", now - timedelta(days=5)),
            ("new_cache_1", now + timedelta(days=1)),
            ("new_cache_2", now + timedelta(days=2)),
        ]

        for cache_key, expires_at in cache_entries:
            await CacheMetadataCRUD.create_cache_metadata(
                test_db_session, cache_key, "test", expires_at
            )

        cleanup_stats = await cleanup_old_data(test_db_session, days=7)

        assert cleanup_stats["cache_metadata_deleted"] == 2

        remaining_cache = await CacheMetadataCRUD.get_cache_statistics(test_db_session)
        assert remaining_cache["total_keys"] == 2

    async def test_cleanup_with_no_old_data(self, test_db_session):

        now = datetime.utcnow()

        await CacheMetadataCRUD.create_cache_metadata(
            test_db_session, "new_cache", "test", now + timedelta(days=1)
        )

        cleanup_stats = await cleanup_old_data(test_db_session, days=7)

        assert cleanup_stats["exchange_data_deleted"] == 0
        assert cleanup_stats["cache_metadata_deleted"] == 0

        remaining_cache = await CacheMetadataCRUD.get_cache_statistics(test_db_session)
        assert remaining_cache["total_keys"] == 1


class TestGetDatabaseStats:
    async def test_get_database_stats_with_data(self, test_db_session, multiple_yield_products):

        create_data_list = [
            YieldProductCreate(**product_data) for product_data in multiple_yield_products
        ]
        created_products = await bulk_upsert_products(test_db_session, create_data_list)

        exchange_data_list = []
        for product in created_products:
            exchange_data = {
                "product_id": product.id,
                "exchange": "TestExchange",
                "raw_data": {"test": "data"},
                "response_status": 200,
                "response_time_ms": 150,
            }
            exchange_data_list.append(exchange_data)

        await bulk_create_exchange_data(test_db_session, exchange_data_list)

        await CacheMetadataCRUD.create_cache_metadata(
            test_db_session, "test_cache", "test", datetime.utcnow() + timedelta(hours=1)
        )

        stats = await get_database_stats(test_db_session)

        assert stats["total_products"] == len(created_products)
        assert stats["active_products"] == len(created_products)
        assert stats["total_exchange_data"] == len(exchange_data_list)
        assert stats["total_cache_entries"] == 1
        assert stats["providers_count"] > 0
        assert stats["symbols_count"] > 0
        assert stats["avg_apy"] > 0
        assert stats["max_apy"] > 0
        assert stats["min_apy"] > 0

    async def test_get_database_stats_with_empty_database(self, test_db_session):
        stats = await get_database_stats(test_db_session)

        assert stats["total_products"] == 0
        assert stats["active_products"] == 0
        assert stats["total_exchange_data"] == 0
        assert stats["total_cache_entries"] == 0
        assert stats["providers_count"] == 0
        assert stats["symbols_count"] == 0
        assert stats["avg_apy"] == 0.0
        assert stats["max_apy"] == 0.0
        assert stats["min_apy"] == 0.0

    async def test_get_database_stats_with_mixed_data(self, test_db_session):

        products_data = [
            {
                "symbol": "BTC",
                "name": "Bitcoin Active",
                "provider": "Binance",
                "apy": 5.0,
                "is_cefi": True,
                "is_active": True,
            },
            {
                "symbol": "ETH",
                "name": "Ethereum Inactive",
                "provider": "Bybit",
                "apy": 8.0,
                "is_cefi": True,
                "is_active": False,
            },
            {
                "symbol": "USDT",
                "name": "Tether Active",
                "provider": "Binance",
                "apy": 3.0,
                "is_cefi": True,
                "is_active": True,
            },
        ]

        create_data_list = [YieldProductCreate(**product_data) for product_data in products_data]
        created_products = await bulk_upsert_products(test_db_session, create_data_list)

        active_products = [p for p in created_products if p.is_active]
        exchange_data_list = []
        for product in active_products:
            exchange_data = {
                "product_id": product.id,
                "exchange": "TestExchange",
                "raw_data": {"test": "data"},
                "response_status": 200,
                "response_time_ms": 150,
            }
            exchange_data_list.append(exchange_data)

        await bulk_create_exchange_data(test_db_session, exchange_data_list)

        stats = await get_database_stats(test_db_session)

        assert stats["total_products"] == 3
        assert stats["active_products"] == 2
        assert stats["total_exchange_data"] == 2
        assert stats["providers_count"] == 2  # Binance, Bybit
        assert stats["symbols_count"] == 3  # BTC, ETH, USDT
        assert stats["avg_apy"] == pytest.approx(5.33, rel=1e-2)  # (5.0 + 8.0 + 3.0) / 3
        assert stats["max_apy"] == 8.0
        assert stats["min_apy"] == 3.0


class TestBulkOperationsPerformance:
    async def test_bulk_upsert_performance(self, test_db_session):
        import time

        products_data = []
        for i in range(100):
            product_data = {
                "symbol": f"TEST{i % 10}",
                "name": f"Test Product {i}",
                "provider": f"Provider{i % 5}",
                "apy": 5.0 + (i % 20),
                "is_cefi": True,
                "min_amount": 0.001,
            }
            products_data.append(YieldProductCreate(**product_data))

        start_time = time.time()
        created_products = await bulk_upsert_products(test_db_session, products_data)
        end_time = time.time()

        assert len(created_products) == 100
        assert (end_time - start_time) < 10.0

    async def test_bulk_create_exchange_data_performance(
        self, test_db_session, multiple_yield_products
    ):
        import time

        create_data_list = [
            YieldProductCreate(**product_data) for product_data in multiple_yield_products
        ]
        created_products = await bulk_upsert_products(test_db_session, create_data_list)

        exchange_data_list = []
        for i in range(200):
            product = created_products[i % len(created_products)]
            exchange_data = {
                "product_id": product.id,
                "exchange": f"Exchange{i % 10}",
                "raw_data": {"test": f"data_{i}", "index": i},
                "response_status": 200,
                "response_time_ms": 150 + (i % 50),
            }
            exchange_data_list.append(exchange_data)

        start_time = time.time()
        created_exchanges = await bulk_create_exchange_data(test_db_session, exchange_data_list)
        end_time = time.time()

        assert len(created_exchanges) == 200
        assert (end_time - start_time) < 15.0

    async def test_cleanup_performance(self, test_db_session):
        import time

        now = datetime.utcnow()

        for i in range(50):
            cache_key = f"old_cache_{i}"
            expires_at = now - timedelta(days=10 + i)
            await CacheMetadataCRUD.create_cache_metadata(
                test_db_session, cache_key, "test", expires_at
            )

        start_time = time.time()
        cleanup_stats = await cleanup_old_data(test_db_session, days=7)
        end_time = time.time()

        assert cleanup_stats["cache_metadata_deleted"] == 50
        assert (end_time - start_time) < 5.0
