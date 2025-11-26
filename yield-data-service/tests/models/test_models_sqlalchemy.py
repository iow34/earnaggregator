"""
Тести для SQLAlchemy моделей.

Тестує створення та функціональність SQLAlchemy моделей:
- Створення таблиць
- Перевірка колонок та типів
- Перевірка constraints та індексів
- Relationships між таблицями
"""

import pytest
from sqlalchemy import text, inspect
from sqlalchemy.exc import IntegrityError
from datetime import datetime

from app.db.models import (
    YieldProductDB, ExchangeDataDB, CacheMetadataDB,
    UserAnalyticsDB, SystemMetricsDB, APILogsDB,
    get_table_names, get_model_by_table_name, get_foreign_key_relationships
)


class TestTableCreation:
    """Тести для створення таблиць."""
    
    async def test_tables_exist(self, test_database_manager):
        """Тест існування всіх таблиць."""
        async with test_database_manager as db_manager:
            inspector = inspect(db_manager.engine.sync_engine)
        existing_tables = inspector.get_table_names()
        
        expected_tables = [
            "yield_products",
            "exchange_data", 
            "cache_metadata",
            "user_analytics",
            "system_metrics",
            "api_logs"
        ]
        
        for table in expected_tables:
            assert table in existing_tables, f"Таблиця {table} не існує"
    
    def test_yield_products_table_structure(self, test_database_manager):
        """Тест структури таблиці yield_products."""
        inspector = inspect(test_database_manager.engine.sync_engine)
        columns = inspector.get_columns("yield_products")
        
        # Перевіряємо основні колонки
        column_names = [col["name"] for col in columns]
        expected_columns = [
            "id", "symbol", "name", "provider", "apy", "is_cefi",
            "min_amount", "max_amount", "lock_period_days", "max_apy",
            "risk_level", "is_active", "website_url", "description",
            "created_at", "updated_at", "last_checked"
        ]
        
        for col in expected_columns:
            assert col in column_names, f"Колонка {col} не існує в yield_products"
    
    def test_exchange_data_table_structure(self, test_database_manager):
        """Тест структури таблиці exchange_data."""
        inspector = inspect(test_database_manager.engine.sync_engine)
        columns = inspector.get_columns("exchange_data")
        
        column_names = [col["name"] for col in columns]
        expected_columns = [
            "id", "product_id", "exchange", "raw_data", "api_endpoint",
            "request_timestamp", "response_status", "response_time_ms"
        ]
        
        for col in expected_columns:
            assert col in column_names, f"Колонка {col} не існує в exchange_data"
    
    def test_cache_metadata_table_structure(self, test_database_manager):
        """Тест структури таблиці cache_metadata."""
        inspector = inspect(test_database_manager.engine.sync_engine)
        columns = inspector.get_columns("cache_metadata")
        
        column_names = [col["name"] for col in columns]
        expected_columns = [
            "id", "cache_key", "cache_type", "created_at", "expires_at",
            "last_accessed", "access_count", "hit_count", "miss_count", "data_size_bytes"
        ]
        
        for col in expected_columns:
            assert col in column_names, f"Колонка {col} не існує в cache_metadata"


class TestDataTypes:
    """Тести для типів даних."""
    
    def test_yield_products_data_types(self, test_database_manager):
        """Тест типів даних в yield_products."""
        inspector = inspect(test_database_manager.engine.sync_engine)
        columns = inspector.get_columns("yield_products")
        
        column_types = {col["name"]: col["type"] for col in columns}
        
        # Перевіряємо типи основних колонок
        assert "VARCHAR" in str(column_types["id"])
        assert "VARCHAR" in str(column_types["symbol"])
        assert "VARCHAR" in str(column_types["name"])
        assert "VARCHAR" in str(column_types["provider"])
        assert "FLOAT" in str(column_types["apy"]) or "DOUBLE" in str(column_types["apy"])
        assert "BOOLEAN" in str(column_types["is_cefi"])
        assert "BOOLEAN" in str(column_types["is_active"])
        assert "TIMESTAMP" in str(column_types["created_at"])
    
    def test_exchange_data_data_types(self, test_database_manager):
        """Тест типів даних в exchange_data."""
        inspector = inspect(test_database_manager.engine.sync_engine)
        columns = inspector.get_columns("exchange_data")
        
        column_types = {col["name"]: col["type"] for col in columns}
        
        # Перевіряємо типи основних колонок
        assert "INTEGER" in str(column_types["id"])
        assert "VARCHAR" in str(column_types["product_id"])
        assert "VARCHAR" in str(column_types["exchange"])
        assert "JSON" in str(column_types["raw_data"])
        assert "TIMESTAMP" in str(column_types["request_timestamp"])


class TestConstraints:
    """Тести для constraints."""
    
    def test_yield_products_primary_key(self, test_database_manager):
        """Тест primary key в yield_products."""
        inspector = inspect(test_database_manager.engine.sync_engine)
        pk_columns = inspector.get_pk_constraint("yield_products")
        
        assert "id" in pk_columns["constrained_columns"]
    
    def test_exchange_data_primary_key(self, test_database_manager):
        """Тест primary key в exchange_data."""
        inspector = inspect(test_database_manager.engine.sync_engine)
        pk_columns = inspector.get_pk_constraint("exchange_data")
        
        assert "id" in pk_columns["constrained_columns"]
    
    def test_foreign_key_constraints(self, test_database_manager):
        """Тест foreign key constraints."""
        inspector = inspect(test_database_manager.engine.sync_engine)
        fk_constraints = inspector.get_foreign_keys("exchange_data")
        
        # Перевіряємо foreign key на product_id
        fk_found = False
        for fk in fk_constraints:
            if "product_id" in fk["constrained_columns"]:
                fk_found = True
                assert fk["referred_table"] == "yield_products"
                assert "id" in fk["referred_columns"]
                break
        
        assert fk_found, "Foreign key constraint не знайдено"


class TestIndexes:
    """Тести для індексів."""
    
    def test_yield_products_indexes(self, test_database_manager):
        """Тест індексів в yield_products."""
        inspector = inspect(test_database_manager.engine.sync_engine)
        indexes = inspector.get_indexes("yield_products")
        
        index_names = [idx["name"] for idx in indexes]
        
        # Перевіряємо наявність основних індексів
        expected_indexes = [
            "idx_yield_products_symbol",
            "idx_yield_products_provider", 
            "idx_yield_products_apy",
            "idx_yield_products_is_active"
        ]
        
        for expected_idx in expected_indexes:
            assert any(expected_idx in name for name in index_names), f"Індекс {expected_idx} не знайдено"
    
    def test_exchange_data_indexes(self, test_database_manager):
        """Тест індексів в exchange_data."""
        inspector = inspect(test_database_manager.engine.sync_engine)
        indexes = inspector.get_indexes("exchange_data")
        
        index_names = [idx["name"] for idx in indexes]
        
        # Перевіряємо наявність основних індексів
        expected_indexes = [
            "idx_exchange_data_exchange",
            "idx_exchange_data_product_id",
            "idx_exchange_data_timestamp"
        ]
        
        for expected_idx in expected_indexes:
            assert any(expected_idx in name for name in index_names), f"Індекс {expected_idx} не знайдено"


class TestRelationships:
    """Тести для relationships між таблицями."""
    
    async def test_yield_product_to_exchange_data_relationship(self, test_db_session, sample_yield_product_data):
        """Тест relationship між YieldProduct та ExchangeData."""
        # Створюємо продукт
        product = YieldProductDB(**sample_yield_product_data)
        test_db_session.add(product)
        await test_db_session.commit()
        await test_db_session.refresh(product)
        
        # Створюємо exchange data
        exchange_data = ExchangeDataDB(
            product_id=product.id,
            exchange="Binance",
            raw_data={"test": "data"},
            api_endpoint="/test",
            response_status=200,
            response_time_ms=150
        )
        test_db_session.add(exchange_data)
        await test_db_session.commit()
        await test_db_session.refresh(exchange_data)
        
        # Перевіряємо relationship
        assert len(product.exchange_data) == 1
        assert product.exchange_data[0].exchange == "Binance"
        assert exchange_data.product.id == product.id
    
    async def test_cascade_delete(self, test_db_session, sample_yield_product_data):
        """Тест cascade delete."""
        # Створюємо продукт
        product = YieldProductDB(**sample_yield_product_data)
        test_db_session.add(product)
        await test_db_session.commit()
        await test_db_session.refresh(product)
        
        # Створюємо exchange data
        exchange_data = ExchangeDataDB(
            product_id=product.id,
            exchange="Binance",
            raw_data={"test": "data"}
        )
        test_db_session.add(exchange_data)
        await test_db_session.commit()
        await test_db_session.refresh(exchange_data)
        
        # Видаляємо продукт
        await test_db_session.delete(product)
        await test_db_session.commit()
        
        # Перевіряємо що exchange_data також видалено
        remaining_exchange_data = await test_db_session.get(ExchangeDataDB, exchange_data.id)
        assert remaining_exchange_data is None


class TestModelCreation:
    """Тести для створення моделей."""
    
    async def test_yield_product_creation(self, test_db_session, sample_yield_product_data):
        """Тест створення YieldProductDB."""
        product = YieldProductDB(**sample_yield_product_data)
        test_db_session.add(product)
        await test_db_session.commit()
        await test_db_session.refresh(product)
        
        assert product.id == sample_yield_product_data["id"]
        assert product.symbol == sample_yield_product_data["symbol"]
        assert product.apy == sample_yield_product_data["apy"]
        assert product.is_active is True
        assert product.created_at is not None
        assert product.updated_at is not None
    
    async def test_exchange_data_creation(self, test_db_session, sample_yield_product_data, sample_exchange_data):
        """Тест створення ExchangeDataDB."""
        # Спочатку створюємо продукт
        product = YieldProductDB(**sample_yield_product_data)
        test_db_session.add(product)
        await test_db_session.commit()
        await test_db_session.refresh(product)
        
        # Створюємо exchange data
        exchange_data = ExchangeDataDB(**sample_exchange_data)
        test_db_session.add(exchange_data)
        await test_db_session.commit()
        await test_db_session.refresh(exchange_data)
        
        assert exchange_data.product_id == sample_exchange_data["product_id"]
        assert exchange_data.exchange == sample_exchange_data["exchange"]
        assert exchange_data.raw_data == sample_exchange_data["raw_data"]
        assert exchange_data.request_timestamp is not None
    
    async def test_cache_metadata_creation(self, test_db_session, sample_cache_metadata):
        """Тест створення CacheMetadataDB."""
        cache_metadata = CacheMetadataDB(**sample_cache_metadata)
        test_db_session.add(cache_metadata)
        await test_db_session.commit()
        await test_db_session.refresh(cache_metadata)
        
        assert cache_metadata.cache_key == sample_cache_metadata["cache_key"]
        assert cache_metadata.cache_type == sample_cache_metadata["cache_type"]
        assert cache_metadata.hit_count == sample_cache_metadata["hit_count"]
        assert cache_metadata.miss_count == sample_cache_metadata["miss_count"]
        assert cache_metadata.created_at is not None


class TestUtilityFunctions:
    """Тести для утилітарних функцій."""
    
    def test_get_table_names(self):
        """Тест функції get_table_names()."""
        table_names = get_table_names()
        
        expected_tables = [
            "yield_products",
            "exchange_data",
            "cache_metadata",
            "user_analytics",
            "system_metrics",
            "api_logs"
        ]
        
        for table in expected_tables:
            assert table in table_names
    
    def test_get_model_by_table_name(self):
        """Тест функції get_model_by_table_name()."""
        # Тестуємо валідні назви таблиць
        assert get_model_by_table_name("yield_products") == YieldProductDB
        assert get_model_by_table_name("exchange_data") == ExchangeDataDB
        assert get_model_by_table_name("cache_metadata") == CacheMetadataDB
        
        # Тестуємо невалідну назву
        assert get_model_by_table_name("nonexistent_table") is None
    
    def test_get_foreign_key_relationships(self):
        """Тест функції get_foreign_key_relationships()."""
        relationships = get_foreign_key_relationships()
        
        assert "yield_products" in relationships
        assert "exchange_data" in relationships["yield_products"]
        assert relationships["yield_products"]["exchange_data"] == "one-to-many"
        
        assert "exchange_data" in relationships
        assert "yield_products" in relationships["exchange_data"]
        assert relationships["exchange_data"]["yield_products"] == "many-to-one"


class TestDataIntegrity:
    """Тести для цілісності даних."""
    
    async def test_unique_constraints(self, test_db_session, sample_yield_product_data):
        """Тест унікальних constraints."""
        # Створюємо перший продукт
        product1 = YieldProductDB(**sample_yield_product_data)
        test_db_session.add(product1)
        await test_db_session.commit()
        
        # Спробуємо створити другий продукт з тим самим ID
        product2_data = sample_yield_product_data.copy()
        product2 = YieldProductDB(**product2_data)
        test_db_session.add(product2)
        
        with pytest.raises(IntegrityError):
            await test_db_session.commit()
    
    async def test_foreign_key_constraint(self, test_db_session):
        """Тест foreign key constraint."""
        # Спробуємо створити exchange_data з неіснуючим product_id
        exchange_data = ExchangeDataDB(
            product_id="nonexistent_id",
            exchange="Binance",
            raw_data={"test": "data"}
        )
        test_db_session.add(exchange_data)
        
        with pytest.raises(IntegrityError):
            await test_db_session.commit()
    
    async def test_not_null_constraints(self, test_db_session):
        """Тест NOT NULL constraints."""
        # Спробуємо створити продукт без обов'язкових полів
        product = YieldProductDB(
            # id відсутній
            symbol="BTC",
            name="Test",
            provider="Test",
            apy=5.0
        )
        test_db_session.add(product)
        
        with pytest.raises(IntegrityError):
            await test_db_session.commit()
