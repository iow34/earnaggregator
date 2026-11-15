"""
Welcome message content loader.
"""

from pathlib import Path
from typing import Optional

CURRENT_DIR = Path(__file__).parent


def get_welcome_message(language: str = "en") -> str:

    if language not in ["ua", "ru", "en"]:
        language = "en"

    file_path = CURRENT_DIR / language / "welcome.txt"

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read().strip()
    except FileNotFoundError:
        fallback_path = CURRENT_DIR / "en" / "welcome.txt"
        with open(fallback_path, "r", encoding="utf-8") as f:
            return f.read().strip()


__all__ = ["get_welcome_message"]
