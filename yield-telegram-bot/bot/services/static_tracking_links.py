import json
import os
from typing import Dict, Optional
from pathlib import Path

from bot.utils.logger import logger
from bot.config import settings


class StaticTrackingLinks:
    _STATIC_LINKS_DATA = {
        "description": "Deployment-specific exchange tracking links",
        "version": "1.1",
        "links": {
            exchange: {
                f"page_{page}": f"{str(settings.TRACKING_REDIRECT_URL).rstrip('/')}/ref?telegram_id={{telegram_id}}&source=organic&page={page}&exchange={exchange}"
                for page in range(1, 4)
            }
            for exchange in (
                "binance",
                "bybit",
                "bitmart",
                "okx",
                "mexc",
                "gate",
                "bitget",
                "kraken",
                "kucoin",
                "htx",
            )
        },
    }

    def __init__(self, links_file: str = None):
        self.links_file = Path(links_file) if links_file else None
        self._links_data = self._STATIC_LINKS_DATA.copy()
        self._load_links_from_file()

    def _load_links_from_file(self) -> None:
        if not self.links_file:
            logger.info("ℹ️ Використовуються вбудовані статичні трекінгові посилання")
            return

        try:
            if self.links_file.exists():
                with open(self.links_file, "r", encoding="utf-8") as f:
                    file_data = json.load(f)

                if "links" in file_data:
                    self._links_data["links"] = file_data["links"]
                    self._links_data["last_updated"] = file_data.get("last_updated", "from_file")
                    logger.info(f"✅ Оновлено статичні трекінгові посилання з {self.links_file}")
                else:
                    logger.warning(f"⚠️ Файл {self.links_file} не містить секції 'links'")
            else:
                logger.info(
                    f"ℹ️ Файл {self.links_file} не знайдено, використовуються вбудовані дані"
                )
        except Exception as e:
            logger.error(f"❌ Помилка завантаження статичних посилань з файлу: {e}")
            logger.info("ℹ️ Продовжуємо з вбудованими даними")

    def reload_links(self) -> None:
        self._load_links()

    def get_tracking_link(
        self, exchange: str, page: int = 1, telegram_id: int = None
    ) -> Optional[str]:
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

            if telegram_id and "{telegram_id}" in link_template:
                link = link_template.replace("{telegram_id}", str(telegram_id))
            else:
                link = link_template

            return link

        except Exception as e:
            logger.error(
                f"❌ Помилка отримання трекінгового посилання для {exchange} сторінка {page}: {e}"
            )
            return None

    def get_all_exchanges(self) -> list[str]:
        if not self._links_data or "links" not in self._links_data:
            return []
        return list(self._links_data["links"].keys())

    def get_exchange_pages(self, exchange: str) -> list[int]:
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

            for exchange, exchange_links in links.items():
                if not isinstance(exchange_links, dict):
                    logger.error(f"❌ Посилання для біржі '{exchange}' повинні бути об'єктом")
                    return False

                for page_key, link in exchange_links.items():
                    if not page_key.startswith("page_"):
                        logger.warning(
                            f"⚠️ Ключ '{page_key}' для біржі '{exchange}' не починається з 'page_'"
                        )

                    if not isinstance(link, str) or not link.startswith("http"):
                        logger.error(
                            f"❌ Посилання '{link}' для '{exchange}:{page_key}' не є коректним URL"
                        )
                        return False

                    if "{telegram_id}" not in link:
                        logger.warning(
                            f"⚠️ Посилання '{link}' для '{exchange}:{page_key}' does not contain the {{telegram_id}} placeholder"
                        )

            logger.info("✅ Файл з посиланнями коректний")
            return True

        except Exception as e:
            logger.error(f"❌ Помилка валідації файлу: {e}")
            return False


static_tracking_links = StaticTrackingLinks()
