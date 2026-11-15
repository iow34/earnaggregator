from pathlib import Path
from typing import Optional
from functools import lru_cache

from bot.utils.logger import logger


def _get_content_dir() -> Path:
    current_file = Path(__file__).resolve()
    return current_file.parent


@lru_cache(maxsize=10)
def load_help_text(lang: str = "ua") -> Optional[str]:

    if lang not in ["ua", "en", "ru"]:
        logger.warning(f"Невірна мова: {lang}, використовую ua")
        lang = "ua"

    content_dir = _get_content_dir()
    file_path = content_dir / lang / "help.txt"

    try:
        if not file_path.exists():
            logger.error(f"Файл довідки не знайдено: {file_path}")
            return None

        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read().strip()

        if not content:
            logger.warning(f"Файл довідки пустий: {file_path}")
            return None

        logger.debug(f"Завантажено довідку: {lang}")
        return content

    except Exception as e:
        logger.error(f"Помилка читання файлу {file_path}: {e}", exc_info=True)
        return None


def clear_cache():
    load_help_text.cache_clear()
    logger.info("Кеш довідки очищено")
