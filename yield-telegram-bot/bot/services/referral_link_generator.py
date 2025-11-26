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


class ReferralLinkGenerator:
    """Генератор реферальних посилань через redirect server."""
    
    def __init__(self):
        """Ініціалізація генератора."""
        # URL redirect server - використовуємо публічну адресу для HTML посилань
        # (DATA_SERVICE_URL - внутрішня Docker адреса для API викликів)
        # (TRACKING_REDIRECT_URL - публічна адреса для трекінгових посилань)
        tracking_url = getattr(settings, 'TRACKING_REDIRECT_URL', None)
        if tracking_url:
            self.redirect_base_url = str(tracking_url).rstrip('/')
        else:
            # Fallback на DATA_SERVICE_URL якщо TRACKING_REDIRECT_URL не встановлено
            self.redirect_base_url = str(settings.DATA_SERVICE_URL).rstrip('/')
        
        # Реферальні коди з .env
        self.referral_codes = settings.referral_urls
    
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
        # КРИТИЧНА ПЕРЕВІРКА: Для telegram_id=0 або негативних значень (кеш/плейсхолдер)
        # НЕ генеруємо трекінгові посилання - використовуємо прямі реферальні посилання
        # Це запобігає створенню тимчасових UUID які не існують в БД
        if not telegram_id or telegram_id <= 0:
            logger.info(
                f"ℹ️ Telegram ID={telegram_id} є плейсхолдером (кеш/система). "
                f"Використовуємо прямі реферальні посилання без трекінгу."
            )
            return self._get_direct_link(exchange, ref_code)
        
        # КРОК 1: Отримати source (спроба реєстрації опціональна)
        # ВАРІАНТ 2: Для простого трекінгу не обов'язково реєструвати користувача
        # Просто використовуємо organic як source за замовчуванням
        source = 'organic'
        
        # Опціональна спроба отримати source через реєстрацію (не критично)
        try:
            user_info = await tracking_client.get_user_info(telegram_id)
            if not user_info:
                # Спроба швидкої реєстрації (тільки для отримання source)
                user_info = await tracking_client.register_user(
                    telegram_id=telegram_id,
                    payload=None  # organic
                )
            
            if user_info:
                source = user_info.get('acquisition_source', 'organic')
                logger.debug(f"ℹ️ Source отримано: {source} для {telegram_id}")
        except Exception as e:
            logger.debug(f"ℹ️ Не вдалося отримати source для {telegram_id}, використовуємо organic: {e}")
            # Продовжуємо з organic source - це не критично
            source = 'organic'
        
        # КРОК 2: Нормалізація page номера
        # Замінюємо 'N' на '3' (список бірж - це сторінка 3)
        normalized_page = page if page != 'N' else '3'
        
        # КРОК 3: Отримати реферальний код з .env якщо не передано
        if not ref_code:
            ref_code = self._get_ref_code_from_env(exchange)
        
        # КРОК 4: Сформувати трекінгове URL через redirect server
        # ВАРІАНТ 2: Використовуємо telegram_id напряму замість user_uuid
        try:
            params = {
                'telegram_id': str(telegram_id),  # Замість 'user' використовуємо 'telegram_id'
                'source': source,
                'page': normalized_page,
                'exchange': exchange.lower()
            }
            
            if ref_code:
                params['ref_code'] = ref_code
            
            # Побудувати query string з правильним кодуванням URL
            query_string = urlencode(params)
            redirect_url = f"{self.redirect_base_url}/ref?{query_string}"
            
            logger.info(
                f"🔗 Згенеровано просте трекінгове посилання: telegram_id={telegram_id}, "
                f"exchange={exchange}, page={normalized_page}"
            )
            
            # Перевірка валідності URL перед поверненням
            if not redirect_url or not redirect_url.startswith('http'):
                logger.error(f"❌ Сформоване трекінгове посилання некоректне: {redirect_url}")
                # Fallback на пряме посилання
                return self._get_direct_link(exchange, ref_code)
            
            # КРИТИЧНА ПЕРЕВІРКА: якщо URL містить localhost/127.0.0.1/yield-api - Telegram не може перейти на нього
            # Логуємо попередження, handlers повинні замінити на прямі реферальні посилання
            if 'localhost' in redirect_url or '127.0.0.1' in redirect_url or 'yield-api' in redirect_url:
                logger.warning(
                    f"⚠️ Згенероване трекінгове посилання містить localhost/yield-api для {exchange}: {redirect_url[:80]}... "
                    f"Handlers повинні замінити на прямі реферальні посилання (Telegram не може перейти на внутрішні адреси Docker)"
                )
            
            return redirect_url
            
        except Exception as e:
            logger.error(f"❌ Критична помилка генерації посилання для {telegram_id}: {e}", exc_info=True)
            
            # При помилці повертаємо прямі реферальні посилання замість трекінгових
            # Це краще ніж генерувати тимчасовий UUID який не існує в БД
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

