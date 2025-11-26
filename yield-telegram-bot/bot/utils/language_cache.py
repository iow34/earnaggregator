"""
Language-aware Cache Manager для Telegram бота.

Забезпечує:
- Кешування з прив'язкою до мови
- Автоматична інвалідація при зміні мови
- Підтримка мультимовності (UA/RU/EN)
- Моніторинг ефективності кешу по мовах
"""

import asyncio
from typing import Any, Callable, List, Optional
from datetime import datetime, UTC

from bot.utils.cache_manager import cache_manager
from bot.utils.logger import logger
from bot.utils.metrics import metrics_collector

# Метрики для моніторингу по мовах
try:
    from prometheus_client import Counter
    
    CACHE_HITS_BY_LANG = Counter(
        'cache_hits_by_language',
        'Cache hits by language',
        ['lang', 'cache_key']
    )
    
    CACHE_MISSES_BY_LANG = Counter(
        'cache_misses_by_language',
        'Cache misses by language',
        ['lang', 'cache_key']
    )
except ImportError:
    CACHE_HITS_BY_LANG = None
    CACHE_MISSES_BY_LANG = None


class LanguageAwareCacheManager:
    """
    Менеджер кешу з підтримкою мультимовності.
    
    Забезпечує коректне кешування для різних мов та автоматичну
    інвалідацію при зміні мови користувачем.
    """
    
    SUPPORTED_LANGUAGES = ["ua", "ru", "en"]
    
    def __init__(self):
        self.cache_stats = {
            "ua": {"hits": 0, "misses": 0, "invalidations": 0},
            "ru": {"hits": 0, "misses": 0, "invalidations": 0},
            "en": {"hits": 0, "misses": 0, "invalidations": 0},
        }
    
    async def get_localized_data(
        self,
        key_prefix: str,
        lang: str,
        refresh_func: Callable,
        ttl: int = 300
    ) -> Any:
        """
        Отримати локалізовані дані з кешу.
        
        Args:
            key_prefix: Префікс ключа (наприклад, "main_menu")
            lang: Код мови (ua/ru/en)
            refresh_func: Асинхронна функція для оновлення даних
            ttl: Час життя кешу в секундах
            
        Returns:
            Дані з кешу або оновлені дані
        """
        if lang not in self.SUPPORTED_LANGUAGES:
            logger.warning(f"⚠️ Непідтримувана мова: {lang}, fallback на 'ua'")
            lang = "ua"
        
        cache_key = f"{key_prefix}:v1:{lang}"
        
        # Спроба отримати з кешу
        cached_data = await cache_manager.get(cache_key)
        
        if cached_data is not None:
            logger.info(f"✅ Дані '{key_prefix}' отримано з кешу ({lang})")
            self.cache_stats[lang]["hits"] += 1
            
            if CACHE_HITS_BY_LANG:
                CACHE_HITS_BY_LANG.labels(lang=lang, cache_key=key_prefix).inc()
            
            return cached_data
        
        # Cache miss - оновлюємо дані
        logger.info(f"🔄 Cache miss для '{key_prefix}' ({lang}), оновлення...")
        self.cache_stats[lang]["misses"] += 1
        
        if CACHE_MISSES_BY_LANG:
            CACHE_MISSES_BY_LANG.labels(lang=lang, cache_key=key_prefix).inc()
        
        try:
            data = await refresh_func()
            
            if data is not None:
                success = await cache_manager.set(cache_key, data, ttl=ttl)
                if success:
                    logger.info(f"💾 Дані '{key_prefix}' збережено в кеш ({lang})")
                else:
                    logger.warning(f"⚠️ Не вдалося зберегти дані '{key_prefix}' в кеш ({lang})")
            
            return data
            
        except Exception as e:
            logger.error(f"❌ Помилка оновлення даних '{key_prefix}' ({lang}): {e}", exc_info=True)
            return None
    
    async def invalidate_language_cache(
        self,
        key_prefix: str,
        lang: str
    ) -> bool:
        """
        Інвалідувати кеш для конкретної мови.
        
        Args:
            key_prefix: Префікс ключа
            lang: Код мови
            
        Returns:
            True якщо успішно інвалідовано
        """
        if lang not in self.SUPPORTED_LANGUAGES:
            logger.warning(f"⚠️ Непідтримувана мова для інвалідації: {lang}")
            return False
        
        cache_key = f"{key_prefix}:v1:{lang}"
        deleted = await cache_manager.delete(cache_key)
        
        if deleted:
            logger.info(f"🗑️ Кеш '{cache_key}' інвалідовано")
            self.cache_stats[lang]["invalidations"] += 1
        else:
            logger.debug(f"ℹ️ Кеш '{cache_key}' не знайдено для інвалідації")
        
        return deleted
    
    async def invalidate_all_language_caches(
        self,
        key_prefix: str
    ) -> int:
        """
        Інвалідувати кеш для всіх мов.
        
        Args:
            key_prefix: Префікс ключа
            
        Returns:
            Кількість інвалідованих ключів
        """
        count = await cache_manager.clear_pattern(f"{key_prefix}:v1:*")
        logger.info(f"🗑️ Інвалідовано {count} кеш-ключів для '{key_prefix}'")
        
        # Оновлюємо статистику
        for lang in self.SUPPORTED_LANGUAGES:
            self.cache_stats[lang]["invalidations"] += 1
        
        return count
    
    async def prefetch_all_languages(
        self,
        key_prefix: str,
        refresh_func: Callable[[str], Any],
        ttl: int = 300
    ) -> dict:
        """
        Попередньо завантажити кеш для всіх мов.
        
        Args:
            key_prefix: Префікс ключа
            refresh_func: Функція що приймає lang і повертає дані
            ttl: Час життя кешу
            
        Returns:
            Словник з результатами для кожної мови
        """
        logger.info(f"🔥 Prefetch кешу '{key_prefix}' для всіх мов...")
        
        tasks = []
        for lang in self.SUPPORTED_LANGUAGES:
            task = self.get_localized_data(
                key_prefix,
                lang,
                lambda l=lang: refresh_func(l),  # Closure для збереження lang
                ttl=ttl
            )
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        prefetch_results = {}
        for lang, result in zip(self.SUPPORTED_LANGUAGES, results):
            if isinstance(result, Exception):
                logger.error(f"❌ Помилка prefetch для {lang}: {result}")
                prefetch_results[lang] = None
            else:
                logger.info(f"✅ Prefetch для {lang} завершено")
                prefetch_results[lang] = result
        
        return prefetch_results
    
    async def warmup_cache(
        self,
        key_prefix: str,
        refresh_func: Callable[[str], Any],
        ttl: int = 300
    ) -> None:
        """
        Розігріти кеш для всіх мов при старті бота.
        
        Args:
            key_prefix: Префікс ключа
            refresh_func: Функція що приймає lang і повертає дані
            ttl: Час життя кешу
        """
        logger.info(f"🔥 Warmup кешу '{key_prefix}'...")
        start_time = datetime.now(UTC)
        
        results = await self.prefetch_all_languages(key_prefix, refresh_func, ttl)
        
        duration = (datetime.now(UTC) - start_time).total_seconds()
        success_count = sum(1 for r in results.values() if r is not None)
        
        logger.info(
            f"✅ Warmup завершено за {duration:.2f}с "
            f"({success_count}/{len(self.SUPPORTED_LANGUAGES)} успішно)"
        )
    
    def get_cache_stats(self) -> dict:
        """
        Отримати статистику кешу по мовах.
        
        Returns:
            Словник зі статистикою для кожної мови
        """
        stats_with_ratio = {}
        
        for lang, stats in self.cache_stats.items():
            hits = stats["hits"]
            misses = stats["misses"]
            total = hits + misses
            hit_ratio = hits / total if total > 0 else 0.0
            
            stats_with_ratio[lang] = {
                **stats,
                "total_requests": total,
                "hit_ratio": f"{hit_ratio:.2%}"
            }
        
        return stats_with_ratio
    
    async def handle_language_change(
        self,
        user_id: int,
        old_lang: str,
        new_lang: str,
        key_prefixes: Optional[List[str]] = None
    ) -> None:
        """
        Обробити зміну мови користувачем.
        
        Інвалідує кеш для нової мови, щоб гарантувати свіжі дані.
        
        Args:
            user_id: ID користувача
            old_lang: Стара мова
            new_lang: Нова мова
            key_prefixes: Список префіксів для інвалідації (за замовчуванням ["main_menu"])
        """
        if key_prefixes is None:
            key_prefixes = ["main_menu"]
        
        logger.info(f"🌐 Користувач {user_id}: зміна мови {old_lang} → {new_lang}")
        
        for prefix in key_prefixes:
            # Інвалідуємо кеш для нової мови
            await self.invalidate_language_cache(prefix, new_lang)
            
            # Опціонально: інвалідуємо кеш для старої мови
            # (можна вимкнути для економії ресурсів)
            # await self.invalidate_language_cache(prefix, old_lang)
        
        logger.info(f"✅ Кеш інвалідовано для {len(key_prefixes)} префіксів")


# Глобальний екземпляр
language_cache = LanguageAwareCacheManager()

