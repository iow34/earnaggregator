"""
Статичні трекінгові посилання для бірж.

Цей модуль надає доступ до статичних трекінгових посилань,
які зберігаються в окремому JSON файлі і можуть бути легко змінені вручну.
"""

import json
import os
from typing import Dict, Optional
from pathlib import Path

from bot.utils.logger import logger


class StaticTrackingLinks:
    """Клас для роботи зі статичними трекінговими посиланнями."""

    def __init__(self, links_file: str = None):
        """
        Ініціалізація статичних трекінгових посилань.

        Args:
            links_file: Шлях до файлу з посиланнями (опціонально)
        """
        if links_file is None:
            # Шлях відносно цього файлу
            current_dir = Path(__file__).parent
            links_file = current_dir.parent / "static_tracking_links.json"

        self.links_file = Path(links_file)
        self._links_data = None
        self._load_links()

    def _load_links(self) -> None:
        """Завантажити посилання з JSON файлу."""
        try:
            if self.links_file.exists():
                with open(self.links_file, 'r', encoding='utf-8') as f:
                    self._links_data = json.load(f)
                logger.info(f"✅ Завантажено статичні трекінгові посилання з {self.links_file}")
            else:
                logger.warning(f"⚠️ Файл з статичними посиланнями не знайдено: {self.links_file}")
                self._links_data = {"links": {}}
        except Exception as e:
            logger.error(f"❌ Помилка завантаження статичних посилань: {e}")
            self._links_data = {"links": {}}

    def reload_links(self) -> None:
        """Перезавантажити посилання з файлу (корисно після ручних змін)."""
        self._load_links()

    def get_tracking_link(self, exchange: str, page: int = 1, telegram_id: int = None) -> Optional[str]:
        """
        Отримати трекінгове посилання для біржі та сторінки.

        Args:
            exchange: Назва біржі (binance, bybit, etc.)
            page: Номер сторінки (1, 2, 3, etc.)
            telegram_id: Telegram ID користувача для персоналізації

        Returns:
            Трекінгове посилання або None якщо не знайдено
        """
        try:
            if not self._links_data or "links" not in self._links_data:
                return None

            exchange_links = self._links_data["links"].get(exchange.lower())
            if not exchange_links:
                logger.warning(f"⚠️ Посилання для біржі '{exchange}' не знайдені")
                return None

            page_key = f"page_{page}"
            link_template = exchange_links.get(page_key)
            if not link_template:
                logger.warning(f"⚠️ Посилання для сторінки {page} біржі '{exchange}' не знайдене")
                return None

            # Замінюємо плейсхолдер telegram_id якщо він є
            if telegram_id and "{telegram_id}" in link_template:
                link = link_template.replace("{telegram_id}", str(telegram_id))
            else:
                link = link_template

            return link

        except Exception as e:
            logger.error(f"❌ Помилка отримання трекінгового посилання для {exchange} сторінка {page}: {e}")
            return None

    def get_all_exchanges(self) -> list[str]:
        """Отримати список всіх доступних бірж."""
        if not self._links_data or "links" not in self._links_data:
            return []
        return list(self._links_data["links"].keys())

    def get_exchange_pages(self, exchange: str) -> list[int]:
        """Отримати список доступних сторінок для біржі."""
        try:
            if not self._links_data or "links" not in self._links_data:
                return []

            exchange_links = self._links_data["links"].get(exchange.lower())
            if not exchange_links:
                return []

            pages = []
            for key, value in exchange_links.items():
                if key.startswith("page_"):
                    try:
                        page_num = int(key.split("_")[1])
                        pages.append(page_num)
                    except (ValueError, IndexError):
                        continue

            return sorted(pages)

        except Exception as e:
            logger.error(f"❌ Помилка отримання сторінок для {exchange}: {e}")
            return []

    def validate_links_file(self) -> bool:
        """
        Перевірити коректність файлу з посиланнями.

        Returns:
            True якщо файл коректний, False якщо є помилки
        """
        try:
            if not self._links_data:
                logger.error("❌ Дані посилань не завантажені")
                return False

            if "links" not in self._links_data:
                logger.error("❌ Секція 'links' відсутня в файлі")
                return False

            links = self._links_data["links"]
            if not isinstance(links, dict):
                logger.error("❌ Секція 'links' повинна бути об'єктом")
                return False

            # Перевіряємо кожну біржу
            for exchange, exchange_links in links.items():
                if not isinstance(exchange_links, dict):
                    logger.error(f"❌ Посилання для біржі '{exchange}' повинні бути об'єктом")
                    return False

                for page_key, link in exchange_links.items():
                    if not page_key.startswith("page_"):
                        logger.warning(f"⚠️ Ключ '{page_key}' для біржі '{exchange}' не починається з 'page_'")

                    if not isinstance(link, str) or not link.startswith("http"):
                        logger.error(f"❌ Посилання '{link}' для '{exchange}:{page_key}' не є коректним URL")
                        return False

                    if "{telegram_id}" not in link:
                        logger.warning(f"⚠️ Посилання '{link}' для '{exchange}:{page_key}' не містить {telegram_id} плейсхолдера")

            logger.info("✅ Файл з посиланнями коректний")
            return True

        except Exception as e:
            logger.error(f"❌ Помилка валідації файлу: {e}")
            return False


# Глобальний екземпляр для використання в усьому додатку
static_tracking_links = StaticTrackingLinks()
