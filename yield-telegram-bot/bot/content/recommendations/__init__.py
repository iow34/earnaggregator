from pathlib import Path
from typing import Dict, Optional
from functools import lru_cache

from bot.utils.logger import logger


RECOMMENDATIONS_METADATA = {
    "rec1": {
        "title": {
            "ua": "Переказ між біржами",
            "ru": "Переводы между биржами",
            "en": "Transfers Between Exchanges",
        },
        "emoji": "🛡️",
    },
    "rec2": {
        "title": {
            "ua": "Flexible vs Locked",
            "ru": "Flexible vs Locked",
            "en": "Flexible vs Locked",
        },
        "emoji": "🔄",
    },
    "rec3": {
        "title": {
            "ua": "Критерії вибору продуктів",
            "ru": "Критерии выбора продуктов",
            "en": "Product Selection Criteria",
        },
        "emoji": "📊",
    },
    "rec4": {
        "title": {
            "ua": "Диверсифікація інвестицій",
            "ru": "Диверсификация инвестиций",
            "en": "Investment Diversification",
        },
        "emoji": "🌐",
    },
    "rec5": {
        "title": {
            "ua": "Моніторинг APY та ризиків",
            "ru": "Мониторинг APY и рисков",
            "en": "APY and Risk Monitoring",
        },
        "emoji": "📈",
    },
    "rec6": {
        "title": {
            "ua": "Реферальні програми",
            "ru": "Реферальные программы",
            "en": "Referral Programs",
        },
        "emoji": "💰",
    },
    "rec7": {
        "title": {
            "ua": "Компаундинг доходу",
            "ru": "Компаундинг дохода",
            "en": "Yield Compounding",
        },
        "emoji": "🔁",
    },
    "rec8": {
        "title": {"ua": "Зниження ризиків", "ru": "Снижение рисков", "en": "Risk Reduction"},
        "emoji": "🛡️",
    },
    "rec9": {
        "title": {
            "ua": "Перевірка надійності біржі",
            "ru": "Проверка надежности биржи",
            "en": "Exchange Reliability Check",
        },
        "emoji": "🔍",
    },
    "rec10": {
        "title": {
            "ua": "Планування портфеля",
            "ru": "Планирование портфеля",
            "en": "Portfolio Planning",
        },
        "emoji": "🎯",
    },
}


def _get_content_dir() -> Path:
    current_file = Path(__file__).resolve()
    return current_file.parent


@lru_cache(maxsize=50)
def load_recommendation(rec_id: str, lang: str = "ua") -> Optional[str]:

    if rec_id not in RECOMMENDATIONS_METADATA:
        logger.warning(f"Невірний rec_id: {rec_id}")
        return None

    if lang not in ["ua", "en", "ru"]:
        logger.warning(f"Невірна мова: {lang}, використовую ua")
        lang = "ua"

    content_dir = _get_content_dir()
    file_path = content_dir / lang / f"{rec_id}.txt"

    try:
        if not file_path.exists():
            logger.error(f"Файл рекомендації не знайдено: {file_path}")
            return None

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

    if lang not in ["ua", "en", "ru"]:
        logger.warning(f"Невірна мова: {lang}, використовую ua")
        lang = "ua"

    return RECOMMENDATIONS_METADATA.copy()


def clear_cache():
    load_recommendation.cache_clear()
    logger.info("Кеш рекомендацій очищено")


def get_all_recommendation_ids() -> list:
    return list(RECOMMENDATIONS_METADATA.keys())
