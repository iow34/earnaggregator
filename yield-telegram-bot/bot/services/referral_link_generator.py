import os
import uuid
import asyncio
from urllib.parse import urlencode
from typing import Optional, Dict
from bot.config import settings
from bot.utils.logger import logger
from bot.services.tracking_client import tracking_client
from bot.services.static_tracking_links import static_tracking_links


class ReferralLinkGenerator:
    def __init__(self):

        self.referral_codes = settings.referral_urls

    @property
    def redirect_base_url(self) -> str:

        tracking_url = getattr(settings, "TRACKING_REDIRECT_URL", None)
        if tracking_url:
            return str(tracking_url).rstrip("/")
        else:
            return str(settings.TRACKING_REDIRECT_URL).rstrip("/")

    async def generate_link(
        self, telegram_id: int, exchange: str, page: str, ref_code: Optional[str] = None
    ) -> str:

        if not telegram_id or telegram_id <= 0:
            logger.info(
                f"ℹ️ Telegram ID={telegram_id} є плейсхолдером. Використовуємо прямі посилання."
            )
            return self._get_direct_link(exchange, ref_code)

        try:
            page_int = int(page)
            if page_int < 1:
                page_int = 1
            elif page_int > 3:
                page_int = 3
        except (ValueError, TypeError):
            page_int = 1

        tracking_url = static_tracking_links.get_tracking_link(
            exchange=exchange, page=page_int, telegram_id=telegram_id
        )

        if tracking_url:
            logger.info(
                f"🔗 Використано статичне трекінгове посилання для {exchange} сторінка {page_int}"
            )
            return tracking_url
        else:
            logger.warning(
                f"⚠️ Статичне посилання не знайдено для {exchange} сторінка {page_int}, використано fallback"
            )
            return self._get_direct_link(exchange, ref_code)

    def _get_ref_code_from_env(self, exchange: str) -> Optional[str]:
        exchange_lower = exchange.lower()

        exchange_mapping = {
            "binance": "binance",
            "bybit": "bybit",
            "okx": "okx",
            "mexc": "mexc",
            "bitmart": "bitmart",
            "gate": "gate",
            "bitget": "bitget",
            "kraken": "kraken",
            "kucoin": "kucoin",
            "htx": "htx",
            "nexo": "nexo",
        }

        key = exchange_mapping.get(exchange_lower)
        if not key:
            logger.warning(f"⚠️ Невідома біржа для реферального коду: {exchange}")
            return None

        referral_url = self.referral_codes.get(key)

        if not referral_url or "YOUR_REF" in referral_url:
            logger.debug(f"ℹ️ Реферальний код не налаштовано для {exchange}")
            return None

        try:
            if "ref=" in referral_url:
                ref_code = referral_url.split("ref=")[1].split("&")[0]
                return ref_code
            elif "referralCode=" in referral_url:
                ref_code = referral_url.split("referralCode=")[1].split("&")[0]
                return ref_code
            else:
                return None
        except Exception as e:
            logger.error(f"❌ Помилка парсингу реферального коду для {exchange}: {e}")
            return None

    def _get_direct_link(self, exchange: str, ref_code: Optional[str] = None) -> str:
        exchange_lower = exchange.lower()
        referral_url = self.referral_codes.get(exchange_lower)

        if referral_url and "YOUR_REF" not in referral_url:
            return referral_url

        # Fallback URLs
        fallback_urls = {
            "binance": "https://www.binance.com",
            "bybit": "https://www.bybit.com",
            "okx": "https://www.okx.com",
            "mexc": "https://www.mexc.com",
            "bitmart": "https://www.bitmart.com",
            "gate": "https://www.gate.io",
            "bitget": "https://www.bitget.com",
            "kraken": "https://www.kraken.com",
            "kucoin": "https://www.kucoin.com",
            "htx": "https://www.htx.com",
            "nexo": "https://nexo.io",
        }

        return fallback_urls.get(exchange_lower, "https://www.binance.com")

    async def generate_links_for_exchanges(
        self, telegram_id: int, exchanges: list, page: str
    ) -> Dict[str, str]:
        links = {}

        for exchange in exchanges:
            link = await self.generate_link(telegram_id=telegram_id, exchange=exchange, page=page)
            links[exchange] = link

        return links


referral_link_generator = ReferralLinkGenerator()
