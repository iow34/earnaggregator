"""
Тести для CRUD операцій з Cache metadata.

Тестує всі CRUD операції для CacheMetadataCRUD:
- Створення cache metadata
- Отримання по cache_key
- Оновлення статистики (hit_count, miss_count)
- Отримання expired ключів
- Видалення expired cache
- Отримання статистики кешу
"""

import pytest
from datetime import datetime, timedelta
from typing import List

from app.db.crud import CacheMetadataCRUD


class TestCacheMetadataCRUD:
    """Тести для CacheMetadataCRUD."""
    
    async def test_create_cache_metadata(self, test_db_session, sample_cache_metadata):
        """Тест створення cache metadata."""
        created_cache = await CacheMetadataCRUD.create_cache_metadata(
            test_db_session,
            sample_cache_metadata["cache_key"],
            sample_cache_metadata["cache_type"],
            sample_cache_metadata["expires_at"],
            sample_cache_metadata.get("data_size_bytes")
        )
        
        assert created_cache.cache_key == sample_cache_metadata["cache_key"]
        assert created_cache.cache_type == sample_cache_metadata["cache_type"]
        assert created_cache.expires_at == sample_cache_metadata["expires_at"]
        assert created_cache.data_size_bytes == sample_cache_metadata.get("data_size_bytes")
        assert created_cache.created_at is not None
        assert created_cache.last_accessed is not None
        assert created_cache.access_count == 0
        assert created_cache.hit_count == 0
        assert created_cache.miss_count == 0
    
    async def test_get_cache_metadata(self, test_db_session, sample_cache_metadata):
        """Тест отримання cache metadata по ключу."""
        # Створюємо cache metadata
        created_cache = await CacheMetadataCRUD.create_cache_metadata(
            test_db_session,
            sample_cache_metadata["cache_key"],
            sample_cache_metadata["cache_type"],
            sample_cache_metadata["expires_at"]
        )
        
        # Отримуємо cache metadata
        retrieved_cache = await CacheMetadataCRUD.get_cache_metadata(
            test_db_session, sample_cache_metadata["cache_key"]
        )
        
        assert retrieved_cache is not None
        assert retrieved_cache.cache_key == sample_cache_metadata["cache_key"]
        assert retrieved_cache.cache_type == sample_cache_metadata["cache_type"]
    
    async def test_get_cache_metadata_not_found(self, test_db_session):
        """Тест отримання неіснуючого cache metadata."""
        retrieved_cache = await CacheMetadataCRUD.get_cache_metadata(
            test_db_session, "nonexistent_key"
        )
        
        assert retrieved_cache is None
    
    async def test_update_cache_metadata(self, test_db_session, sample_cache_metadata):
        """Тест оновлення cache metadata."""
        # Створюємо cache metadata
        created_cache = await CacheMetadataCRUD.create_cache_metadata(
            test_db_session,
            sample_cache_metadata["cache_key"],
            sample_cache_metadata["cache_type"],
            sample_cache_metadata["expires_at"]
        )
        
        # Оновлюємо cache metadata
        update_data = {
            "hit_count": 5,
            "miss_count": 2,
            "access_count": 7,
            "data_size_bytes": 2048
        }
        
        updated_cache = await CacheMetadataCRUD.update_cache_metadata(
            test_db_session, sample_cache_metadata["cache_key"], update_data
        )
        
        assert updated_cache is not None
        assert updated_cache.hit_count == 5
        assert updated_cache.miss_count == 2
        assert updated_cache.access_count == 7
        assert updated_cache.data_size_bytes == 2048
    
    async def test_update_nonexistent_cache_metadata(self, test_db_session):
        """Тест оновлення неіснуючого cache metadata."""
        update_data = {"hit_count": 5}
        
        updated_cache = await CacheMetadataCRUD.update_cache_metadata(
            test_db_session, "nonexistent_key", update_data
        )
        
        assert updated_cache is None
    
    async def test_delete_cache_metadata(self, test_db_session, sample_cache_metadata):
        """Тест видалення cache metadata."""
        # Створюємо cache metadata
        created_cache = await CacheMetadataCRUD.create_cache_metadata(
            test_db_session,
            sample_cache_metadata["cache_key"],
            sample_cache_metadata["cache_type"],
            sample_cache_metadata["expires_at"]
        )
        
        # Видаляємо cache metadata
        result = await CacheMetadataCRUD.delete_cache_metadata(
            test_db_session, sample_cache_metadata["cache_key"]
        )
        
        assert result is True
        
        # Перевіряємо що cache metadata видалено
        deleted_cache = await CacheMetadataCRUD.get_cache_metadata(
            test_db_session, sample_cache_metadata["cache_key"]
        )
        assert deleted_cache is None
    
    async def test_delete_nonexistent_cache_metadata(self, test_db_session):
        """Тест видалення неіснуючого cache metadata."""
        result = await CacheMetadataCRUD.delete_cache_metadata(
            test_db_session, "nonexistent_key"
        )
        
        assert result is False
    
    async def test_get_expired_cache_keys(self, test_db_session):
        """Тест отримання expired cache ключів."""
        now = datetime.utcnow()
        
        # Створюємо cache metadata з різними expires_at
        cache_keys = [
            ("expired_key_1", now - timedelta(hours=1)),  # Expired
            ("expired_key_2", now - timedelta(minutes=30)),  # Expired
            ("active_key_1", now + timedelta(hours=1)),  # Active
            ("active_key_2", now + timedelta(minutes=30))  # Active
        ]
        
        for cache_key, expires_at in cache_keys:
            await CacheMetadataCRUD.create_cache_metadata(
                test_db_session, cache_key, "test", expires_at
            )
        
        # Отримуємо expired ключі
        expired_keys = await CacheMetadataCRUD.get_expired_cache_keys(test_db_session)
        
        assert len(expired_keys) == 2
        assert all(key in ["expired_key_1", "expired_key_2"] for key in expired_keys)
    
    async def test_delete_expired_cache(self, test_db_session):
        """Тест видалення expired cache."""
        now = datetime.utcnow()
        
        # Створюємо cache metadata з різними expires_at
        cache_keys = [
            ("expired_key_1", now - timedelta(hours=1)),  # Expired
            ("expired_key_2", now - timedelta(minutes=30)),  # Expired
            ("active_key_1", now + timedelta(hours=1)),  # Active
        ]
        
        for cache_key, expires_at in cache_keys:
            await CacheMetadataCRUD.create_cache_metadata(
                test_db_session, cache_key, "test", expires_at
            )
        
        # Видаляємо expired cache
        deleted_count = await CacheMetadataCRUD.delete_expired_cache(test_db_session)
        
        assert deleted_count == 2
        
        # Перевіряємо що тільки активні ключі залишилися
        active_cache = await CacheMetadataCRUD.get_cache_metadata(test_db_session, "active_key_1")
        assert active_cache is not None
        
        expired_cache = await CacheMetadataCRUD.get_cache_metadata(test_db_session, "expired_key_1")
        assert expired_cache is None
    
    async def test_get_cache_statistics(self, test_db_session):
        """Тест отримання статистики кешу."""
        # Створюємо кілька cache metadata з різною статистикою
        cache_entries = [
            ("cache_key_1", "yield", 10, 5, 15, 1024),
            ("cache_key_2", "yield", 8, 2, 10, 2048),
            ("cache_key_3", "top", 15, 3, 18, 512),
            ("cache_key_4", "recommendations", 5, 1, 6, 256)
        ]
        
        for cache_key, cache_type, hit_count, miss_count, access_count, data_size in cache_entries:
            created_cache = await CacheMetadataCRUD.create_cache_metadata(
                test_db_session, cache_key, cache_type, datetime.utcnow() + timedelta(hours=1)
            )
            
            # Оновлюємо статистику
            await CacheMetadataCRUD.update_cache_metadata(
                test_db_session, cache_key, {
                    "hit_count": hit_count,
                    "miss_count": miss_count,
                    "access_count": access_count,
                    "data_size_bytes": data_size
                }
            )
        
        # Отримуємо статистику
        stats = await CacheMetadataCRUD.get_cache_statistics(test_db_session)
        
        assert stats["total_keys"] == 4
        assert stats["total_hits"] == 38  # 10 + 8 + 15 + 5
        assert stats["total_misses"] == 11  # 5 + 2 + 3 + 1
        assert stats["total_accesses"] == 49  # 15 + 10 + 18 + 6
        assert stats["hit_rate_percent"] == pytest.approx(77.55, rel=1e-2)  # 38 / 49 * 100
        assert stats["total_size_bytes"] == 3840  # 1024 + 2048 + 512 + 256
        
        # Перевіряємо статистику по типах
        assert stats["by_type"]["yield"]["count"] == 2
        assert stats["by_type"]["yield"]["hits"] == 18
        assert stats["by_type"]["top"]["count"] == 1
        assert stats["by_type"]["top"]["hits"] == 15
    
    async def test_get_cache_statistics_by_type(self, test_db_session):
        """Тест отримання статистики кешу по типах."""
        # Створюємо cache metadata різних типів
        cache_types = ["yield", "top", "recommendations", "yield", "top"]
        
        for i, cache_type in enumerate(cache_types):
            cache_key = f"cache_{cache_type}_{i}"
            created_cache = await CacheMetadataCRUD.create_cache_metadata(
                test_db_session, cache_key, cache_type, datetime.utcnow() + timedelta(hours=1)
            )
            
            # Оновлюємо статистику
            await CacheMetadataCRUD.update_cache_metadata(
                test_db_session, cache_key, {
                    "hit_count": i + 1,
                    "miss_count": i,
                    "access_count": (i + 1) * 2
                }
            )
        
        # Отримуємо статистику
        stats = await CacheMetadataCRUD.get_cache_statistics(test_db_session)
        
        # Перевіряємо статистику по типах
        assert stats["by_type"]["yield"]["count"] == 2
        assert stats["by_type"]["top"]["count"] == 2
        assert stats["by_type"]["recommendations"]["count"] == 1
        
        # Перевіряємо що всі типи присутні
        assert "yield" in stats["by_type"]
        assert "top" in stats["by_type"]
        assert "recommendations" in stats["by_type"]


class TestCacheMetadataCRUDEdgeCases:
    """Тести для крайових випадків CacheMetadataCRUD."""
    
    async def test_create_cache_metadata_with_duplicate_key(self, test_db_session):
        """Тест створення cache metadata з дублікатом ключа."""
        cache_key = "duplicate_key"
        expires_at = datetime.utcnow() + timedelta(hours=1)
        
        # Створюємо перший cache metadata
        await CacheMetadataCRUD.create_cache_metadata(
            test_db_session, cache_key, "test", expires_at
        )
        
        # Спробуємо створити другий з тим самим ключем
        with pytest.raises(Exception):  # Має викинути unique constraint error
            await CacheMetadataCRUD.create_cache_metadata(
                test_db_session, cache_key, "test", expires_at
            )
    
    async def test_get_expired_cache_keys_with_no_expired(self, test_db_session):
        """Тест отримання expired ключів коли немає expired."""
        # Створюємо тільки активні cache metadata
        active_keys = ["active_key_1", "active_key_2"]
        for cache_key in active_keys:
            await CacheMetadataCRUD.create_cache_metadata(
                test_db_session, cache_key, "test", datetime.utcnow() + timedelta(hours=1)
            )
        
        # Отримуємо expired ключі
        expired_keys = await CacheMetadataCRUD.get_expired_cache_keys(test_db_session)
        
        assert len(expired_keys) == 0
    
    async def test_delete_expired_cache_with_no_expired(self, test_db_session):
        """Тест видалення expired cache коли немає expired."""
        # Створюємо тільки активні cache metadata
        await CacheMetadataCRUD.create_cache_metadata(
            test_db_session, "active_key", "test", datetime.utcnow() + timedelta(hours=1)
        )
        
        # Видаляємо expired cache
        deleted_count = await CacheMetadataCRUD.delete_expired_cache(test_db_session)
        
        assert deleted_count == 0
        
        # Перевіряємо що активний cache залишився
        active_cache = await CacheMetadataCRUD.get_cache_metadata(test_db_session, "active_key")
        assert active_cache is not None
    
    async def test_get_cache_statistics_with_empty_database(self, test_db_session):
        """Тест отримання статистики кешу з порожньої БД."""
        stats = await CacheMetadataCRUD.get_cache_statistics(test_db_session)
        
        assert stats["total_keys"] == 0
        assert stats["total_hits"] == 0
        assert stats["total_misses"] == 0
        assert stats["total_accesses"] == 0
        assert stats["hit_rate_percent"] == 0.0
        assert stats["total_size_bytes"] == 0
        assert stats["by_type"] == {}


class TestCacheMetadataCRUDPerformance:
    """Тести для продуктивності CacheMetadataCRUD."""
    
    async def test_bulk_operations_performance(self, test_db_session):
        """Тест продуктивності масових операцій."""
        import time
        
        # Створюємо багато cache metadata
        cache_keys = [f"cache_key_{i}" for i in range(100)]
        
        start_time = time.time()
        for i, cache_key in enumerate(cache_keys):
            await CacheMetadataCRUD.create_cache_metadata(
                test_db_session, cache_key, "test", datetime.utcnow() + timedelta(hours=1)
            )
            
            # Оновлюємо статистику
            await CacheMetadataCRUD.update_cache_metadata(
                test_db_session, cache_key, {
                    "hit_count": i + 1,
                    "miss_count": i,
                    "access_count": (i + 1) * 2
                }
            )
        end_time = time.time()
        
        assert (end_time - start_time) < 10.0  # Має зайняти менше 10 секунд
        
        # Перевіряємо статистику
        stats = await CacheMetadataCRUD.get_cache_statistics(test_db_session)
        assert stats["total_keys"] == 100
    
    async def test_get_expired_performance(self, test_db_session):
        """Тест продуктивності отримання expired ключів."""
        import time
        
        # Створюємо багато cache metadata (50% expired, 50% active)
        now = datetime.utcnow()
        for i in range(100):
            cache_key = f"cache_key_{i}"
            expires_at = now - timedelta(hours=1) if i % 2 == 0 else now + timedelta(hours=1)
            
            await CacheMetadataCRUD.create_cache_metadata(
                test_db_session, cache_key, "test", expires_at
            )
        
        # Тестуємо отримання expired ключів
        start_time = time.time()
        expired_keys = await CacheMetadataCRUD.get_expired_cache_keys(test_db_session)
        end_time = time.time()
        
        assert (end_time - start_time) < 1.0  # Має зайняти менше 1 секунди
        assert len(expired_keys) == 50  # 50% expired
