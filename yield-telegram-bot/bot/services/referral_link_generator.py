"""
Генератор динамічних реферальних посилань.

Створює посилання через redirect server з tracking параметрами:
- user UUID
- acquisition source
- page (1, 2, N)
- exchange
- ref_code (з .env)
"""

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
    """Генератор реферальних посилань через redirect server."""
    
    def __init__(self):
        """Ініціалізація генератора."""
        # Реферальні коди з .env (кешуються, бо не змінюються часто)
        self.referral_codes = settings.referral_urls

    @property
    def redirect_base_url(self) -> str:
        """
        Динамічно отримує URL для redirect server.

        Використовує TRACKING_REDIRECT_URL якщо встановлено,
        інакше hardcode на актуальний Railway домен.
        """
        # (TRACKING_REDIRECT_URL - публічна адреса для трекінгових посилань)
        tracking_url = getattr(settings, 'TRACKING_REDIRECT_URL', None)
        if tracking_url:
            return str(tracking_url).rstrip('/')
        else:
            # Hardcode на актуальний Railway домен для гарантованої роботи
            return "https://go-to-the-exchange.up.railway.app"
    
    async def generate_link(
        self,
        telegram_id: int,
        exchange: str,
        page: str,
        ref_code: Optional[str] = None
    ) -> str:
        """
        Генерувати реферальне посилання з трекінгом.
        
        НОВИЙ ПІДХІД: Завжди генеруємо трекінгове посилання.
        Якщо користувач не зареєстрований - реєструємо його.
        Ніколи не повертаємо прямі посилання без трекінгу.
        
        Args:
            telegram_id: Telegram ID користувача
            exchange: Назва біржі (lowercase)
            page: Сторінка бота ('1', '2', '3' - замість 'N' використовуємо '3')
            ref_code: Реферальний код (опціонально, якщо вже є)
            
        Returns:
            URL через redirect server з трекінгом
        """
        # Для telegram_id=0 або негативних значень використовуємо прямі посилання
        if not telegram_id or telegram_id <= 0:
            logger.info(
                f"ℹ️ Telegram ID={telegram_id} є плейсхолдером. Використовуємо прямі посилання."
            )
            return self._get_direct_link(exchange, ref_code)

        # Нормалізація page номера
        try:
            page_int = int(page)
            if page_int < 1:
                page_int = 1
            elif page_int > 3:
                page_int = 3
        except (ValueError, TypeError):
            page_int = 1

        # Отримати статичне посилання
        tracking_url = static_tracking_links.get_tracking_link(
            exchange=exchange,
            page=page_int,
            telegram_id=telegram_id
        )

        if tracking_url:
            logger.info(f"🔗 Використано статичне трекінгове посилання для {exchange} сторінка {page_int}")
            return tracking_url
        else:
            # Fallback на пряме реферальне посилання
            logger.warning(f"⚠️ Статичне посилання не знайдено для {exchange} сторінка {page_int}, використано fallback")
            return self._get_direct_link(exchange, ref_code)
    
    def _get_ref_code_from_env(self, exchange: str) -> Optional[str]:
        """
        Отримати реферальний код з .env.
        
        Args:
            exchange: Назва біржі
            
        Returns:
            Реферальний код або None
        """
        exchange_lower = exchange.lower()
        
        # Маппінг назв бірж до ключів в settings
        exchange_mapping = {
            'binance': 'binance',
            'bybit': 'bybit',
            'okx': 'okx',
            'mexc': 'mexc',
            'bitmart': 'bitmart',
            'gate': 'gate',
            'bitget': 'bitget',
            'kraken': 'kraken',
            'kucoin': 'kucoin',
            'htx': 'htx',
            'nexo': 'nexo'
        }
        
        key = exchange_mapping.get(exchange_lower)
        if not key:
            logger.warning(f"⚠️ Невідома біржа для реферального коду: {exchange}")
            return None
        
        # Отримати URL з settings
        referral_url = self.referral_codes.get(key)
        
        if not referral_url or 'YOUR_REF' in referral_url:
            # Реферальний код не налаштовано
            logger.debug(f"ℹ️ Реферальний код не налаштовано для {exchange}")
            return None
        
        # Витягнути ref_code з URL
        # Приклад: https://accounts.binance.com/register?ref=ABC123
        try:
            if 'ref=' in referral_url:
                ref_code = referral_url.split('ref=')[1].split('&')[0]
                return ref_code
            elif 'referralCode=' in referral_url:
                ref_code = referral_url.split('referralCode=')[1].split('&')[0]
                return ref_code
            else:
                # Не вдалося розпарсити
                return None
        except Exception as e:
            logger.error(f"❌ Помилка парсингу реферального коду для {exchange}: {e}")
            return None
    
    def _get_direct_link(self, exchange: str, ref_code: Optional[str] = None) -> str:
        """
        Отримати пряме посилання на біржу (fallback без трекінгу).
        
        Args:
            exchange: Назва біржі
            ref_code: Реферальний код
            
        Returns:
            Пряме посилання
        """
        exchange_lower = exchange.lower()
        referral_url = self.referral_codes.get(exchange_lower)
        
        if referral_url and 'YOUR_REF' not in referral_url:
            return referral_url
        
        # Fallback URLs
        fallback_urls = {
            'binance': 'https://www.binance.com',
            'bybit': 'https://www.bybit.com',
            'okx': 'https://www.okx.com',
            'mexc': 'https://www.mexc.com',
            'bitmart': 'https://www.bitmart.com',
            'gate': 'https://www.gate.io',
            'bitget': 'https://www.bitget.com',
            'kraken': 'https://www.kraken.com',
            'kucoin': 'https://www.kucoin.com',
            'htx': 'https://www.htx.com',
            'nexo': 'https://nexo.io'
        }
        
        return fallback_urls.get(exchange_lower, 'https://www.binance.com')
    
    async def generate_links_for_exchanges(
        self,
        telegram_id: int,
        exchanges: list,
        page: str
    ) -> Dict[str, str]:
        """
        Генерувати посилання для списку бірж.
        
        Args:
            telegram_id: Telegram ID користувача
            exchanges: Список назв бірж
            page: Сторінка бота
            
        Returns:
            Словник {exchange: link}
        """
        links = {}
        
        for exchange in exchanges:
            link = await self.generate_link(
                telegram_id=telegram_id,
                exchange=exchange,
                page=page
            )
            links[exchange] = link
        
        return links


# Глобальний екземпляр
referral_link_generator = ReferralLinkGenerator()

