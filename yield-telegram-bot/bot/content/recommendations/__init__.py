"""
Content loader для статичних текстів рекомендацій.

Забезпечує:
- Завантаження текстів рекомендацій з файлів
- Кешування завантажених текстів
- Підтримку мультимовності (UA/EN/RU)
- Метадані рекомендацій (назви, емодзі)
"""

from pathlib import Path
from typing import Dict, Optional
from functools import lru_cache

from bot.utils.logger import logger


# Метадані рекомендацій з підтримкою мультимовності
RECOMMENDATIONS_METADATA = {
    "rec1": {
        "title": {
            "ua": "Переказ між біржами",
            "ru": "Переводы между биржами",
            "en": "Transfers Between Exchanges"
        },
        "emoji": "🛡️",
    },
    "rec2": {
        "title": {
            "ua": "Flexible vs Locked",
            "ru": "Flexible vs Locked",
            "en": "Flexible vs Locked"
        },
        "emoji": "🔄",
    },
    "rec3": {
        "title": {
            "ua": "Критерії вибору продуктів",
            "ru": "Критерии выбора продуктов",
            "en": "Product Selection Criteria"
        },
        "emoji": "📊",
    },
    "rec4": {
        "title": {
            "ua": "Диверсифікація інвестицій",
            "ru": "Диверсификация инвестиций",
            "en": "Investment Diversification"
        },
        "emoji": "🌐",
    },
    "rec5": {
        "title": {
            "ua": "Моніторинг APY та ризиків",
            "ru": "Мониторинг APY и рисков",
            "en": "APY and Risk Monitoring"
        },
        "emoji": "📈",
    },
    "rec6": {
        "title": {
            "ua": "Реферальні програми",
            "ru": "Реферальные программы",
            "en": "Referral Programs"
        },
        "emoji": "💰",
    },
    "rec7": {
        "title": {
            "ua": "Компаундинг доходу",
            "ru": "Компаундинг дохода",
            "en": "Yield Compounding"
        },
        "emoji": "🔁",
    },
    "rec8": {
        "title": {
            "ua": "Зниження ризиків",
            "ru": "Снижение рисков",
            "en": "Risk Reduction"
        },
        "emoji": "🛡️",
    },
    "rec9": {
        "title": {
            "ua": "Перевірка надійності біржі",
            "ru": "Проверка надежности биржи",
            "en": "Exchange Reliability Check"
        },
        "emoji": "🔍",
    },
    "rec10": {
        "title": {
            "ua": "Планування портфеля",
            "ru": "Планирование портфеля",
            "en": "Portfolio Planning"
        },
        "emoji": "🎯",
    },
}


def _get_content_dir() -> Path:
    """
    Отримати шлях до директорії з контентом.
    
    Returns:
        Path до директорії recommendations
    """
    current_file = Path(__file__).resolve()
    return current_file.parent


@lru_cache(maxsize=50)
def load_recommendation(rec_id: str, lang: str = "ua") -> Optional[str]:
    """
    Завантажити текст рекомендації з файлу з кешуванням.
    
    Args:
        rec_id: ID рекомендації (rec1, rec2, ..., rec10)
        lang: Мова (ua, en, ru)
    
    Returns:
        Текст рекомендації або None якщо не знайдено
    """
    # Валідація rec_id
    if rec_id not in RECOMMENDATIONS_METADATA:
        logger.warning(f"Невірний rec_id: {rec_id}")
        return None
    
    # Валідація мови
    if lang not in ["ua", "en", "ru"]:
        logger.warning(f"Невірна мова: {lang}, використовую ua")
        lang = "ua"
    
    # Шлях до файлу
    content_dir = _get_content_dir()
    file_path = content_dir / lang / f"{rec_id}.txt"
    
    try:
        if not file_path.exists():
            logger.error(f"Файл рекомендації не знайдено: {file_path}")
            return None
        
        # Читання файлу
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read().strip()
        
        if not content:
            logger.warning(f"Файл рекомендації пустий: {file_path}")
            return None
        
        logger.debug(f"Завантажено рекомендацію: {rec_id} ({lang})")
        return content
    
    except Exception as e:
        logger.error(f"Помилка читання файлу {file_path}: {e}", exc_info=True)
        return None


def get_recommendations_menu(lang: str = "ua") -> Dict[str, Dict[str, str]]:
    """
    Отримати список всіх доступних рекомендацій для меню.
    
    Args:
        lang: Мова (ua, en, ru)
    
    Returns:
        Словник з метаданими рекомендацій
    """
    # Валідація мови
    if lang not in ["ua", "en", "ru"]:
        logger.warning(f"Невірна мова: {lang}, використовую ua")
        lang = "ua"
    
    # Повертаємо копію метаданих
    return RECOMMENDATIONS_METADATA.copy()


def clear_cache():
    """Очистити кеш завантажених рекомендацій."""
    load_recommendation.cache_clear()
    logger.info("Кеш рекомендацій очищено")


def get_all_recommendation_ids() -> list:
    """
    Отримати список всіх ID рекомендацій.
    
    Returns:
        Список ID (rec1, rec2, ..., rec10)
    """
    return list(RECOMMENDATIONS_METADATA.keys())

