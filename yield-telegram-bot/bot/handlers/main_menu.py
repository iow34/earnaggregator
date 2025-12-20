"""
Обробник головного меню (Сторінка 1).

Відображає:
- TOP 10 trending products (на основі CoinGecko trending)
- Групування по біржам (BTC, ETH, SOL, USDT)
- Навігація до різних розділів
"""

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, LinkPreviewOptions
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.filters import Command
from typing import Any, Dict, List, Optional, Tuple

from bot.services.api_client import APIClient, ttl_cache
from bot.keyboards.navigation import main_menu_navigation
from bot.services.referral_link_generator import referral_link_generator
from bot.utils.logger import logger
from bot.utils.cache_manager import cache_manager
from bot.localization import localization
# Імпорт буде всередині функції щоб уникнути циклічного імпорту
from bot.config import settings

import time
import asyncio
from datetime import datetime, UTC

router = Router(name="main_menu_handler")


async def measure_operation_time(operation_name: str, operation_func):
    """
    Виміряти час виконання операції та залогувати якщо потрібно.
    """
    start_time = time.time()

    try:
        result = await operation_func
        duration = time.time() - start_time

        if duration > 0.1:
            logger.info(
                f"⏱️ Операція '{operation_name}' виконана за {duration:.3f}с")

        return result

    except Exception as e:
        duration = time.time() - start_time
        logger.error(
            f"❌ Помилка в операції '{operation_name}' за {duration:.3f}с: {e}")
        raise


class SearchStates(StatesGroup):
    """Стани для розширеного пошуку."""
    waiting_product_input = State()  # Очікування введення продукту вручну


# Пріоритетні символи для швидкого перегляду
PRIORITY_SYMBOLS = ["BTC", "ETH", "SOL", "USDT"]


def _get_referral_url(provider: str) -> str:
    """Отримати реферальне посилання для біржі з config."""
    return settings.referral_urls.get(provider.lower(), "#")


def _format_exchange_display_name(exchange: str) -> str:
    """Форматувати назву біржі для відображення."""
    display_names = {
        "binance": "Binance",
        "bybit": "Bybit",
        "okx": "OKX",
        "mexc": "MEXC",
        "bitmart": "BitMart",
        "gate": "Gate",
        "bitget": "Bitget",
        "kraken": "Kraken",
        "kucoin": "KuCoin",
        "htx": "HTX",
        "nexo": "Nexo",
    }
    return display_names.get(exchange.lower(), exchange.title())


def find_best_flexible_product(
    products: List[Dict], symbol: str, trending_score: int) -> Optional[Dict[str, Any]]:
    """Знаходить найкращий flexible продукт для символу."""
    best_product = None
    best_apy = 0

    for product in products:
        apy = product.get("apy", 0)
        lock_period_days = product.get("lock_period_days", 0)

        if lock_period_days == 0 and apy > best_apy:
            best_apy = apy
            best_product = {
                "symbol": symbol,
                "provider": product.get("provider", "Unknown"),
                "apy": apy,
                "lock_period_days": lock_period_days,
                "trending_score": trending_score
            }

    return best_product


async def get_trending_products_individual(
    api_client: APIClient, trending_coins: List[Dict]) -> List[Dict[str, Any]]:
    """Отримує trending продукти окремими запитами (fallback) з паралельною обробкою."""
    async def get_symbol_data(coin):
        symbol = coin.get("symbol", "").upper()
        try:
            symbol_data = await api_client.get_yield_by_symbol(symbol, limit=20)
            if symbol_data.get("success"):
                products_list = symbol_data.get("data", [])
                if isinstance(products_list, list):
                    return find_best_flexible_product(
                        products_list, symbol, coin.get("score", 0))
        except Exception as e:
            logger.warning(f"Помилка отримання продуктів для {symbol}: {e}")
        return None

    results = []
    for coin in trending_coins:
        try:
            result = await get_symbol_data(coin)
            results.append(result)
        except Exception as e:
            logger.warning(
                f"Помилка при послідовній обробці {coin.get('symbol')}: {e}")
            results.append(None)

    return [
    product for product in results if product is not None and not isinstance(
        product,
         Exception)]


async def generate_main_menu_content(
    api_client, telegram_id: int, lang: str = "ua") -> Dict[str, Any]:
    """
    Генерувати контент головного меню.
    """
    top10_task = measure_operation_time(
    "format_top10_section",
    _format_top_10_section(
        api_client,
         lang))
    exchanges_task = measure_operation_time(
    "format_exchanges_quick_view", _format_exchanges_quick_view(
        api_client, telegram_id, lang))

    results = await asyncio.gather(top10_task, exchanges_task, return_exceptions=True)
    await api_client.close()

    top10_result, exchanges_result = results

    if isinstance(top10_result, Exception):
        logger.warning(
            f"⚠️ Помилка отримання trending продуктів: {top10_result}")
        top10_text = f"📊 <b>{localization.get_text('section.trending_top', lang)}</b>\n{localization.get_text('error.data_unavailable', lang)}\n"
    else:
        top10_text = top10_result

    if isinstance(exchanges_result, Exception):
        logger.warning(f"⚠️ Помилка отримання огляду бірж: {exchanges_result}")
        exchanges_text = f"🏦 <b>{localization.get_text('section.exchanges_overview', lang)}</b>\n{localization.get_text('error.data_unavailable', lang)}\n"
    else:
        exchanges_text = exchanges_result

    text = f"💰 <b>{localization.get_text('section.main_title', lang)}</b>\n\n"
    text += top10_text
    text += "\n━━━━━━━━━━━━━━━━━\n\n"
    text += exchanges_text
    text += "\n━━━━━━━━━━━━━━━━━\n\n"
    text += f"💡 <i>{localization.get_text('section.hint', lang)}</i>"

    return {
        "text": text,
        "generated_at": datetime.now(UTC).isoformat(),
        "version": "v1"
    }


async def show_main_menu(
    message: Message,
    state: FSMContext,
     lang: str = "ua") -> None:
    """
    Показати головне меню з топ продуктами та біржами.
    Використовує language-aware кешування.
    """
    start_time = time.time()

    try:
        # Update language in state if passed
        await state.update_data(lang=lang)

        await cache_manager.initialize()
        telegram_id = message.from_user.id

        # 🔥 Використовуємо language_cache для мультимовного кешування
        from bot.utils.language_cache import language_cache
        
        async def refresh_main_menu():
            api_client = APIClient()
            try:
                return await generate_main_menu_content(api_client, 0, lang)
            finally:
                await api_client.close()

        cached_menu = await language_cache.get_localized_data(
            key_prefix="main_menu",
            lang=lang,
            refresh_func=refresh_main_menu,
            ttl=settings.MAIN_MENU_TTL
        )

        if cached_menu:
            logger.info(f"🎯 Головне меню отримано з кешу ({lang})")
            cached_text = cached_menu["text"]

            # 🔄 Динамічна заміна прямих посилань на трекінгові для кожного користувача
            try:
                exchanges = [
            "binance",
            "bybit",
            "bitmart",
            "okx",
            "mexc",
            "gate",
            "bitget",
            "kraken",
            "kucoin",
             "htx"]

                async def generate_tracking_link(exchange: str):
                    try:
                        tracking_url = await referral_link_generator.generate_link(
                            telegram_id=telegram_id,
                            exchange=exchange,
                            page="1"
                        )
                        if tracking_url and tracking_url.startswith('http'):
                            if 'localhost' not in tracking_url and '127.0.0.1' not in tracking_url and 'yield-api' not in tracking_url:
                                return exchange, tracking_url
                    except Exception as e:
                        logger.warning(
                            f"⚠️ Не вдалося згенерувати трекінгове посилання для {exchange}: {e}")
                    return exchange, None

                tracking_tasks = [generate_tracking_link(
                    exchange) for exchange in exchanges]
                tracking_results = await asyncio.gather(*tracking_tasks)

                for exchange, tracking_url in tracking_results:
                    if tracking_url:
                        direct_url = _get_referral_url(exchange)
                        if direct_url and direct_url != "#":
                            escaped_direct = direct_url.replace('&', '&amp;')
                            escaped_tracking = tracking_url.replace(
                                '&', '&amp;')
                            if escaped_direct in cached_text:
                                cached_text = cached_text.replace(
                                    escaped_direct, escaped_tracking)
                                logger.debug(f"🔗 Замінено пряме посилання на трекінгове для {exchange}")
            except Exception as e:
                logger.error(
    f"❌ Помилка заміни посилань в кешованому меню: {e}",
     exc_info=True)

            await message.answer(
                text=cached_text,
                # Assuming main_menu_navigation accepts lang
                reply_markup=main_menu_navigation(lang),
                parse_mode="HTML",
                link_preview_options=LinkPreviewOptions(is_disabled=True)
            )
            await state.clear()
            # Restore lang after clear
            await state.update_data(current_page="main_menu", lang=lang)
            return

        logger.info("🔄 Генерація головного меню (кеш відсутній)")
        await state.clear()
        await state.update_data(current_page="main_menu", lang=lang)

        api_client = APIClient()
        try:
            menu_data = await generate_main_menu_content(api_client, telegram_id, lang)
            text = menu_data["text"]
        except Exception as e:
            logger.error(
    f"❌ Критична помилка генерації меню: {e}",
     exc_info=True)
            text = (f"💰 <b>{localization.get_text('section.main_title', lang)}</b>\n\n"
                   f"⚠️ {localization.get_text('error.system_unavailable', lang)}\n\n"
                   f"{localization.get_text('error.try_different_criteria', lang)}")
        finally:
            await api_client.close()

        await message.answer(
            text=text,
            reply_markup=main_menu_navigation(lang),
            parse_mode="HTML",
            link_preview_options=LinkPreviewOptions(is_disabled=True)
        )

        duration = time.time() - start_time
        logger.info(
            f"✅ Головне меню згенеровано та показано за {duration:.3f}с")

    except Exception as e:
        logger.error(
    f"❌ Критична помилка в show_main_menu: {e}",
     exc_info=True)
        fallback_text = localization.get_text("error.general", lang)
        await message.answer(text=fallback_text, reply_markup=main_menu_navigation(lang))


async def show_main_page(
    message: Message,
    state: FSMContext,
     lang: str = "ua") -> None:
    """
    Показати головну сторінку з топ продуктами та біржами.
    Це основна функціональна сторінка, доступна через /main.
    """
    start_time = time.time()

    try:
        # Update language in state if passed
        await state.update_data(lang=lang)

        await cache_manager.initialize()
        telegram_id = message.from_user.id

        # 🔥 Використовуємо language_cache для мультимовного кешування
        from bot.utils.language_cache import language_cache

        async def refresh_main_menu():
            api_client = APIClient()
            try:
                return await generate_main_menu_content(api_client, 0, lang)
            finally:
                await api_client.close()

        cached_menu = await language_cache.get_localized_data(
            key_prefix="main_menu",
            lang=lang,
            refresh_func=refresh_main_menu,
            ttl=settings.MAIN_MENU_TTL
        )

        if cached_menu:
            logger.info(f"🎯 Головна сторінка отримана з кешу ({lang})")
            cached_text = cached_menu["text"]

            # 🔄 Динамічна заміна прямих посилань на трекінгові для кожного користувача
            try:
                exchanges = [
            "binance",
            "bybit",
            "bitmart",
            "okx",
            "mexc",
            "gate",
            "bitget",
            "kraken",
            "kucoin",
             "htx"]

                async def generate_tracking_link(exchange: str):
                    try:
                        tracking_url = await referral_link_generator.generate_link(
                            telegram_id=telegram_id,
                            exchange=exchange,
                            page="1"
                        )
                        if tracking_url and tracking_url.startswith('http'):
                            if 'localhost' not in tracking_url and '127.0.0.1' not in tracking_url and 'yield-api' not in tracking_url:
                                return exchange, tracking_url
                    except Exception as e:
                        logger.warning(
                            f"⚠️ Не вдалося згенерувати трекінгове посилання для {exchange}: {e}")
                    return exchange, None

                tracking_tasks = [generate_tracking_link(
                    exchange) for exchange in exchanges]
                tracking_results = await asyncio.gather(*tracking_tasks)

                for exchange, tracking_url in tracking_results:
                    if tracking_url:
                        direct_url = _get_referral_url(exchange)
                        if direct_url and direct_url != "#":
                            escaped_direct = direct_url.replace('&', '&amp;')
                            escaped_tracking = tracking_url.replace(
                                '&', '&amp;')
                            if escaped_direct in cached_text:
                                cached_text = cached_text.replace(
                                    escaped_direct, escaped_tracking)
                                logger.debug(f"🔗 Замінено пряме посилання на трекінгове для {exchange}")
            except Exception as e:
                logger.error(
    f"❌ Помилка заміни посилань в кешованому меню: {e}",
     exc_info=True)

            await message.answer(
                text=cached_text,
                # Assuming main_menu_navigation accepts lang
                reply_markup=main_menu_navigation(lang),
                parse_mode="HTML",
                link_preview_options=LinkPreviewOptions(is_disabled=True)
            )
            await state.clear()
            # Restore lang after clear
            await state.update_data(current_page="main_menu", lang=lang)
            return

        logger.info("🔄 Генерація головної сторінки (кеш відсутній)")
        await state.clear()
        await state.update_data(current_page="main_menu", lang=lang)

        api_client = APIClient()
        try:
            menu_data = await generate_main_menu_content(api_client, telegram_id, lang)
            text = menu_data["text"]
        except Exception as e:
            logger.error(
    f"❌ Критична помилка генерації меню: {e}",
     exc_info=True)
            text = (f"💰 <b>{localization.get_text('section.main_title', lang)}</b>\n\n"
                   f"⚠️ {localization.get_text('error.system_unavailable', lang)}\n\n"
                   f"{localization.get_text('error.try_different_criteria', lang)}")
        finally:
            await api_client.close()

        await message.answer(
            text=text,
            reply_markup=main_menu_navigation(lang),
            parse_mode="HTML",
            link_preview_options=LinkPreviewOptions(is_disabled=True)
        )

        duration = time.time() - start_time
        logger.info(
            f"✅ Головна сторінка згенеровано та показано за {duration:.3f}с")

    except Exception as e:
        logger.error(
    f"❌ Критична помилка в show_main_page: {e}",
     exc_info=True)
        fallback_text = localization.get_text("error.general", lang)
        await message.answer(text=fallback_text, reply_markup=main_menu_navigation(lang))


async def _format_top_10_section(
    api_client: APIClient,
     lang: str = "ua") -> str:
    """Форматувати секцію з топ 10 trending продуктами."""
    try:
        try:
            trending_data = await api_client.get_trending_coins()
        except Exception as api_error:
            # Якщо circuit breaker відкритий або інші проблеми з API
            logger.warning(f"⚠️ API недоступний для trending coins: {api_error}, використовуємо fallback")
            return f"📭 <b>{localization.get_text('section.trending_top', lang)}</b>\n{localization.get_text('error.data_unavailable', lang)}\n"

        if not trending_data.get("success"):
            return f"📭 <b>{localization.get_text('section.trending_top', lang)}</b>\n{localization.get_text('error.data_unavailable', lang)}\n"

        trending_coins = trending_data.get(
    "data", {}).get(
        "trending_coins", [])
        if not trending_coins:
            return f"📊 <b>{localization.get_text('section.trending_top', lang)}</b>\n{localization.get_text('error.data_unavailable', lang)}\n"

        text = f"🚀 <b>{localization.get_text('section.trending_top', lang)}</b>\n\n"
        text += "<pre>"

        # Localized headers
        h_num = localization.get_text("table.header.number", lang)
        h_prod = localization.get_text("table.header.product", lang)
        h_exch = localization.get_text("table.header.exchange", lang)
        h_apy = localization.get_text("table.header.apy", lang)
        h_type = localization.get_text("table.header.type", lang)

        text += f"{h_num}  {h_prod}  {h_exch}     {h_apy}    {h_type}\n"
        text += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"

        trending_products = []

        # 1) Спроба отримати готовий TOP з нового endpoint (top_products)
        try:
            top_resp = await api_client.get_top_products(limit=10)
            if top_resp.get("success") and isinstance(top_resp.get("data"), list):
                for item in top_resp["data"]:
                    best_exchange = item.get("best_exchange") or "N/A"
                    best_apy = float(item.get("best_apy") or 0.0)
                    trending_products.append({
                        "symbol": item.get("symbol", "").upper(),
                        "provider": best_exchange[:9],
                        "apy": best_apy,
                        "lock_period_days": 0,
                        "trending_score": max(0, 100 - (item.get("rank", 10) - 1) * 5)
                    })
        except Exception as e:
            logger.warning(f"⚠️ Помилка top_products endpoint: {e}")

        # 2) Fallback — стара логіка через batch/individual (може бути повільною)
        if not trending_products:
            symbols = [coin.get("symbol", "").upper() for coin in trending_coins[:10]]
            try:
                batch_data = await api_client.get_multiple_yields(symbols, limit=20)
                if batch_data.get("success") and isinstance(batch_data.get("data"), dict):
                    for coin in trending_coins[:10]:
                        symbol = coin.get("symbol", "").upper()
                        symbol_products = batch_data.get("data", {}).get(symbol, [])
                        if isinstance(symbol_products, list) and symbol_products:
                            best_product = find_best_flexible_product(
                                symbol_products, symbol, coin.get("score", 0)
                            )
                            if best_product:
                                trending_products.append(best_product)
            except Exception as e:
                logger.warning(f"⚠️ Помилка batch запиту для trending products: {e}")
        
        if not trending_products:
            try:
                trending_products = await get_trending_products_individual(api_client, trending_coins[:10])
            except Exception as e:
                logger.error(f"❌ Помилка отримання trending products individual: {e}", exc_info=True)
                trending_products = []

        if not trending_products:
            text += "</pre>"
            text += f"\n{localization.get_text('error.nothing_found', lang)}\n"
            return text

        trending_products.sort(
            key=lambda x: x.get("trending_score", 0),
            reverse=True
        )

        for i, product in enumerate(trending_products[:10], 1):
            symbol = product.get("symbol", "???")[:7].ljust(7)
            provider = product.get("provider", "???")[:9].ljust(9)
            apy = product.get("apy", 0)

            if apy >= 1:
                apy_str = f"{apy:.1f}%".rjust(6)
            elif apy >= 0.1:
                apy_str = f"{apy:.2f}%".rjust(6)
            elif apy >= 0.01:
                apy_str = f"{apy:.3f}%".rjust(6)
            else:
                apy_str = f"{apy:.4f}%".rjust(6)

            lock_days = product.get("lock_period_days", 0)
            if lock_days == 0:
                type_str = localization.get_text("table.product.flexible", lang)
            else:
                type_str = f"{lock_days}d"
            
            if type_str == "Flexible":
                type_str = "Flex"
            type_str = type_str.ljust(4)[:4]

            text += f"{i:2d} {symbol} {provider} {apy_str} {type_str}\n"

        text += "</pre>"
        return text

    except Exception as e:
        logger.error(
    f"Помилка форматування trending топ 10: {e}",
     exc_info=True)
        return f"📊 <b>{localization.get_text('section.trending_top', lang)}</b>\n{localization.get_text('error.data_unavailable', lang)}\n"


async def _format_exchanges_quick_view(
    api_client: APIClient,
    telegram_id: int,
     lang: str = "ua") -> str:
    """Форматувати швидкий перегляд по біржам."""
    text = f"🏦 <b>{localization.get_text('section.exchanges_overview', lang)}</b>\n\n"

    try:
        exchanges = [
    "binance",
    "bybit",
    "bitmart",
    "okx",
    "mexc",
    "gate",
    "bitget",
    "kraken",
    "kucoin",
     "htx"]
        tasks = [
    _format_single_exchange_preview(
        api_client,
        exchange,
        telegram_id,
         lang) for exchange in exchanges]
        exchange_texts = await asyncio.gather(*tasks, return_exceptions=True)

        for i, exchange_text in enumerate(exchange_texts):
            if isinstance(exchange_text, Exception):
                exchange = exchanges[i]
                display_name = _format_exchange_display_name(exchange)
                text += f"<b>{display_name}</b>: {localization.get_text('error.data_unavailable', lang)}\n"
            else:
                text += exchange_text + "\n"

        return text
    except Exception as e:
        logger.error(f"Помилка форматування бірж: {e}", exc_info=True)
        return text + \
            f"{localization.get_text('error.data_unavailable', lang)}\n"


async def _format_single_exchange_preview(
    api_client: APIClient,
    exchange: str,
    telegram_id: int,
     lang: str = "ua") -> str:
    """Форматувати попередній перегляд однієї біржі з використанням priority_products."""
    try:
        # Отримуємо priority продукти через оптимізований API
        try:
            priority_data = await api_client.get_priority_products(exchange)
        except Exception as api_error:
            # Якщо circuit breaker відкритий або інші проблеми з API
            logger.warning(f"⚠️ API недоступний для {exchange}: {api_error}, використовуємо fallback")
            return await _format_single_exchange_preview_fallback(api_client, exchange, telegram_id, lang)

        if not priority_data.get("success"):
            # Fallback на старий метод якщо priority_products недоступні
            logger.warning(f"⚠️ Priority products недоступні для {exchange}, використовуємо fallback")
            return await _format_single_exchange_preview_fallback(api_client, exchange, telegram_id, lang)
        
        priority_products = priority_data.get("data", [])
        
        # Логування для дебагу
        logger.info(f"📊 {exchange}: отримано {len(priority_products)} priority продуктів з API")
        if priority_products:
            logger.info(f"📊 {exchange}: перший продукт: {priority_products[0]}")
            # Логуємо APY для всіх продуктів
            for p in priority_products:
                logger.info(f"  - {p.get('symbol')}: apy={p.get('apy')}, type={type(p.get('apy'))}, is_active={p.get('is_active')}")
        
        # Гарантуємо, що є всі 4 продукти в правильному порядку
        if len(priority_products) < 4:
            # Доповнюємо відсутні продукти з APY=0.0
            existing_symbols = {p.get("symbol", "").upper() for p in priority_products}
            for symbol in PRIORITY_SYMBOLS:
                if symbol not in existing_symbols:
                    priority_products.append({
                        "symbol": symbol,
                        "apy": 0.0,
                        "is_active": False
                    })
        
        # Сортуємо за порядком PRIORITY_SYMBOLS
        symbol_order = {symbol: idx for idx, symbol in enumerate(PRIORITY_SYMBOLS)}
        priority_products.sort(key=lambda p: symbol_order.get(p.get("symbol", "").upper(), 999))

        try:
            # Завжди використовуємо трекінгові посилання через generate_link
            referral_url = await referral_link_generator.generate_link(telegram_id=telegram_id, exchange=exchange, page="1")
        except Exception as e:
            logger.warning(f"⚠️ Помилка генерації трекінгового посилання для {exchange}: {e}")
            # Fallback на прямі посилання тільки при критичній помилці
            referral_url = _get_referral_url(exchange)

        if not referral_url or not referral_url.startswith('http'):
            referral_url = "https://www.binance.com"

        escaped_url = referral_url.replace('&', '&amp;')
        display_name = _format_exchange_display_name(exchange)
        text = f"<b>{display_name}</b> <a href=\"{escaped_url}\">{localization.get_text('nav.visit', lang)}</a>\n"

        apy_parts = []
        for product in priority_products[:4]:  # Гарантуємо тільки 4 продукти
            symbol = product.get("symbol", "UNK")
            apy = product.get("apy", 0.0)
            
            # Логування для дебагу
            logger.info(f"🔍 {exchange}/{symbol}: apy={apy}, type={type(apy)}, before_format={apy}")
            
            # Переконуємося що apy є числом
            if isinstance(apy, str):
                try:
                    apy = float(apy)
                except (ValueError, TypeError):
                    logger.warning(f"⚠️ Невдалося конвертувати APY для {exchange}/{symbol}: {apy}")
                    apy = 0.0
            elif not isinstance(apy, (int, float)):
                logger.warning(f"⚠️ Неправильний тип APY для {exchange}/{symbol}: {type(apy)}")
                apy = 0.0
            
            # Форматування APY
            if apy >= 1:
                apy_str = f"{apy:.1f}%"
            elif apy >= 0.1:
                apy_str = f"{apy:.2f}%"
            elif apy >= 0.01:
                apy_str = f"{apy:.3f}%"
            else:
                apy_str = f"{apy:.4f}%" if apy > 0 else "0.0%"
            
            apy_parts.append(f"{symbol} {apy_str}")

        text += f"📊 {' • '.join(apy_parts)}\n"
        text += f"{localization.get_text('nav.show_all_exchange_products', lang, exchange=exchange)}\n"
        return text

    except Exception as e:
        logger.error(
    f"Помилка форматування біржі {exchange}: {e}",
     exc_info=True)
        # Fallback на старий метод при помилці
        try:
            return await _format_single_exchange_preview_fallback(api_client, exchange, telegram_id, lang)
        except Exception as fallback_error:
            logger.error(f"Помилка fallback для {exchange}: {fallback_error}")
            display_name = _format_exchange_display_name(exchange)
            return f"<b>{display_name}</b>: {localization.get_text('error.general', lang)}\n"


async def _format_single_exchange_preview_fallback(
    api_client: APIClient,
    exchange: str,
    telegram_id: int,
     lang: str = "ua") -> str:
    """Fallback метод для форматування біржі (старий спосіб)."""
    try:
        limit_stages = [500, 1000]
        priority_products = []

        for attempt, limit in enumerate(limit_stages, 1):
            try:
                exchange_data = await api_client.get_exchanges(exchange=exchange, limit=limit)
            except Exception as api_error:
                # Якщо circuit breaker відкритий або інші проблеми з API
                logger.warning(f"⚠️ API недоступний для {exchange} (fallback): {api_error}")
                if attempt == len(limit_stages):
                    display_name = _format_exchange_display_name(exchange)
                    return f"<b>{display_name}</b>: {localization.get_text('error.data_unavailable', lang)}"
                continue

            if not exchange_data.get("success"):
                if attempt == len(limit_stages):
                    display_name = _format_exchange_display_name(exchange)
                    return f"<b>{display_name}</b>: {localization.get_text('error.data_unavailable', lang)}"
                continue

            all_exchange_products = exchange_data.get("data", [])
            if not all_exchange_products:
                if attempt == len(limit_stages):
                    display_name = _format_exchange_display_name(exchange)
                    return f"<b>{display_name}</b>: {localization.get_text('error.nothing_found', lang)}"
                continue

            products_by_symbol = {}
            for product in all_exchange_products:
                symbol = product.get("symbol", "").upper()
                if symbol:
                    # Для головної сторінки обираємо тільки flexible продукти
                    lock_period_days = product.get("lock_period_days", 0)
                    is_flexible = lock_period_days == 0

                    # Якщо це не flexible продукт, пропускаємо
                    if not is_flexible:
                        continue

                    if symbol in products_by_symbol:
                        if product.get("apy", 0) > products_by_symbol[symbol].get("apy", 0):
                            products_by_symbol[symbol] = product
                    else:
                        products_by_symbol[symbol] = product

            for symbol in PRIORITY_SYMBOLS:
                if symbol in products_by_symbol and symbol not in [
                    p.get("symbol", "").upper() for p in priority_products]:
                    priority_products.append(products_by_symbol[symbol])

            if len(priority_products) >= 4 or attempt == len(limit_stages):
                break

        # Гарантуємо всі 4 продукти навіть якщо не знайдено
        existing_symbols = {p.get("symbol", "").upper() for p in priority_products}
        for symbol in PRIORITY_SYMBOLS:
            if symbol not in existing_symbols:
                priority_products.append({
                    "symbol": symbol,
                    "apy": 0.0,
                    "is_active": False
                })

        # Сортуємо за порядком PRIORITY_SYMBOLS
        symbol_order = {symbol: idx for idx, symbol in enumerate(PRIORITY_SYMBOLS)}
        priority_products.sort(key=lambda p: symbol_order.get(p.get("symbol", "").upper(), 999))

        try:
            # Завжди використовуємо трекінгові посилання через generate_link
            referral_url = await referral_link_generator.generate_link(telegram_id=telegram_id, exchange=exchange, page="1")
        except Exception as e:
            logger.warning(f"⚠️ Помилка генерації трекінгового посилання для {exchange}: {e}")
            # Fallback на прямі посилання тільки при критичній помилці
            referral_url = _get_referral_url(exchange)

        if not referral_url or not referral_url.startswith('http'):
            referral_url = "https://www.binance.com"

        escaped_url = referral_url.replace('&', '&amp;')
        display_name = _format_exchange_display_name(exchange)
        text = f"<b>{display_name}</b> <a href=\"{escaped_url}\">{localization.get_text('nav.visit', lang)}</a>\n"

        apy_parts = []
        for product in priority_products[:4]:
            symbol = product.get("symbol", "UNK")
            apy = product.get("apy", 0.0)
            if apy >= 1:
                apy_str = f"{apy:.1f}%"
            elif apy >= 0.1:
                apy_str = f"{apy:.2f}%"
            elif apy >= 0.01:
                apy_str = f"{apy:.3f}%"
            else:
                apy_str = f"{apy:.4f}%" if apy > 0 else "0.0%"
            apy_parts.append(f"{symbol} {apy_str}")

        text += f"📊 {' • '.join(apy_parts)}\n"
        text += f"{localization.get_text('nav.show_all_exchange_products', lang, exchange=exchange)}\n"
        return text

    except Exception as e:
        logger.error(f"Помилка fallback форматування біржі {exchange}: {e}", exc_info=True)
        return f"<b>{exchange.title()}</b>: {localization.get_text('error.general', lang)}\n"


@router.callback_query(F.data == "back_to_main")
async def back_to_main_handler(
    callback: CallbackQuery,
     state: FSMContext) -> None:
    """Обробник кнопки повернення на головну з індикатором завантаження."""
    try:
        await callback.answer()
        user_data = await state.get_data()
        lang = user_data.get("lang", "ua")

        # Створюємо задачу для показу індикатора завантаження через 1 секунду
        loading_task = None

        async def show_loading_indicator():
            """Показати індикатор завантаження якщо процес займає >1 сек."""
            try:
                await asyncio.sleep(1.0)
                # Якщо ми досі тут - значить завантаження триває
                loading_text = localization.get_text("loading.main_menu", lang)
                logger.info(f"🌐 back_to_main_handler: Showing loading message in '{lang}': {loading_text}")
                return await callback.message.answer(loading_text)
            except asyncio.CancelledError:
                # Завантаження завершилось швидше 1 секунди
                pass

        # Запускаємо індикатор в фоні
        loading_task = asyncio.create_task(show_loading_indicator())

        try:
            await show_main_menu(callback.message, state, lang)
        finally:
            # Скасовуємо індикатор завантаження, якщо він ще не запустився
            if loading_task and not loading_task.done():
                loading_task.cancel()
                try:
                    await loading_task
                except asyncio.CancelledError:
                    pass

    except Exception as e:
        logger.error(f"Помилка в back_to_main_handler: {e}", exc_info=True)
        await callback.answer("❌ Error")


@router.callback_query(F.data == "all_products")
async def all_products_handler(
    callback: CallbackQuery,
     state: FSMContext) -> None:
    """Показати всі продукти."""
    try:
        user_data = await state.get_data()
        lang = user_data.get("lang", "ua")
        await callback.answer(localization.get_text("loading.products", lang))

        loading_msg = await callback.message.answer(localization.get_text("loading.products", lang))

        from bot.handlers.filtered_products import _display_all_products

        await _display_all_products(loading_msg, state, page=1, is_callback=True)

        if loading_msg.message_id != callback.message.message_id:
            await callback.message.delete()
    except Exception as e:
        logger.error(f"Помилка в all_products_handler: {e}", exc_info=True)


@router.callback_query(F.data == "all_exchanges")
async def all_exchanges_handler(
    callback: CallbackQuery,
     state: FSMContext) -> None:
    """Показати список всіх бірж."""
    try:
        user_data = await state.get_data()
        lang = user_data.get("lang", "ua")
        await callback.answer(localization.get_text("loading.exchanges", lang))
        loading_msg = await callback.message.answer(localization.get_text("loading.exchanges", lang))

        await _display_all_exchanges(loading_msg, state, page=1, is_callback=True, lang=lang)

        if loading_msg.message_id != callback.message.message_id:
            await callback.message.delete()
    except Exception as e:
        logger.error(f"Помилка в all_exchanges_handler: {e}", exc_info=True)


@router.message(Command("main"))
async def main_command_handler(
    message: Message,
    state: FSMContext) -> None:
    """Обробник команди /main - показує головну сторінку з фінансовими даними."""
    try:
        user_data = await state.get_data()
        lang = user_data.get("lang", "ua")

        # Показуємо індикатор завантаження
        loading_text = localization.get_text("loading.main_menu", lang)
        loading_message = await message.answer(loading_text)

        # Викликаємо функцію показу головної сторінки
        await show_main_page(message, state, lang)

        # Видаляємо індикатор завантаження якщо він ще існує
        try:
            await loading_message.delete()
        except Exception:
            pass  # Повідомлення вже могло бути видалено

    except Exception as e:
        logger.error(f"Помилка в main_command_handler: {e}", exc_info=True)
        # Fallback повідомлення
        lang = "ua"  # fallback
        fallback_text = localization.get_text("error.general", lang)
        await message.answer(text=fallback_text)


@router.message(Command("exchanges"))
@router.message(F.text.in_([
    "🏦 Exchanges",     # English
    "🏦 Біржі",        # Ukrainian
    "🏦 Биржи"         # Russian
]))
async def exchanges_command_handler(
    message: Message,
     state: FSMContext) -> None:
    try:
        user_data = await state.get_data()
        lang = user_data.get("lang", "ua")
        loading_msg = await message.answer(localization.get_text("loading.exchanges", lang))
        await _display_all_exchanges(loading_msg, state, page=1, is_callback=False, lang=lang)
    except Exception as e:
        logger.error(f"Помилка в exchanges_command_handler: {e}", exc_info=True)


async def _display_all_exchanges(message, state: FSMContext, page: int = 1, is_callback: bool = False, lang: str = "ua") -> None:
    """Відобразити всі доступні біржі."""
    try:
        await state.update_data(current_page="all_exchanges", page=page, lang=lang)
        telegram_id = message.from_user.id if hasattr(message, "from_user") else message.chat.id

        exchange_names = [
            "binance",
            "bybit",
            "okx",
            "mexc",
            "bitmart",
            "gate",
            "bitget",
            "kraken",
            "kucoin",
            "htx",
            "nexo",
        ]
        display_names = {
            "binance": "Binance",
            "bybit": "Bybit",
            "okx": "OKX",
            "mexc": "MEXC",
            "bitmart": "BitMart",
            "gate": "Gate",
            "bitget": "Bitget",
            "kraken": "Kraken",
            "kucoin": "KuCoin",
            "htx": "HTX",
            "nexo": "Nexo",
        }

        exchanges = []
        for exchange_name in exchange_names:
            try:
                # Завжди використовуємо трекінгові посилання через generate_link
                referral_url = await referral_link_generator.generate_link(
                    telegram_id=telegram_id,
                    exchange=exchange_name,
                    page="3",
                )
            except Exception as e:
                logger.warning(f"⚠️ Помилка генерації трекінгового посилання для {exchange_name}: {e}")
                # Fallback на прямі посилання тільки при критичній помилці
                referral_url = _get_referral_url(exchange_name)

            if not referral_url or not referral_url.startswith("http"):
                referral_url = "https://www.binance.com"

            exchanges.append(
                {
                    "name": exchange_name,
                    "display_name": display_names.get(exchange_name, exchange_name.title()),
                    "url": referral_url,
                }
            )

        items_per_page = 20
        total_exchanges = len(exchanges)
        total_pages = max(1, (total_exchanges + items_per_page - 1) // items_per_page)
        page = max(1, min(page, total_pages))
        start_idx = (page - 1) * items_per_page
        page_exchanges = exchanges[start_idx : start_idx + items_per_page]

        if not page_exchanges:
            text = (
                f"{localization.get_text('error.empty_page', lang)} "
                f"({localization.get_text('nav.page', lang)} {page}/{total_pages})"
            )
            keyboard = _create_exchanges_keyboard(
                page=page,
                total_pages=total_pages,
                has_exchanges=False,
                lang=lang,
            )
        else:
            text = f"{localization.get_text('section.exchanges_list', lang)}\n\n"
            for exchange in page_exchanges:
                escaped_url = exchange["url"].replace("&", "&amp;")
                text += (
                    f"🏦 <b>{exchange['display_name']}</b> "
                    f"<a href=\"{escaped_url}\">{localization.get_text('nav.visit', lang)}</a>\n"
                )
                text += (
                    f"{localization.get_text('nav.show_all_exchange_products', lang, exchange=exchange['name'])}\n\n"
                )

            text += (
                f"📊 {localization.get_text('table.results.shown', lang, shown=len(page_exchanges), total=total_exchanges)} "
                f"({localization.get_text('nav.page', lang)} {page}/{total_pages})"
            )
            keyboard = _create_exchanges_keyboard(
                page=page,
                total_pages=total_pages,
                has_exchanges=True,
                lang=lang,
            )

        if is_callback:
            await message.edit_text(
                text,
                reply_markup=keyboard,
                parse_mode="HTML",
                link_preview_options=LinkPreviewOptions(is_disabled=True),
            )
        else:
            await message.answer(
                text,
                reply_markup=keyboard,
                parse_mode="HTML",
                link_preview_options=LinkPreviewOptions(is_disabled=True),
            )

    except Exception as e:
        logger.error(f"Помилка відображення всіх бірж: {e}", exc_info=True)

def _create_exchanges_keyboard(
    page: int = 1,
    total_pages: int = 1,
    has_exchanges: bool = True,
     lang: str = "ua") -> InlineKeyboardMarkup:
    buttons = []
    if total_pages > 1:
        nav_row = []
        if page > 1:
            nav_row.append(
    InlineKeyboardButton(
        text=localization.get_text(
            "nav.previous",
            lang),
             callback_data=f"exchanges_prev:{page}"))
        nav_row.append(
    InlineKeyboardButton(
            text=f"{page}/{total_pages}",
         callback_data="noop"))
        if page < total_pages:
            nav_row.append(
    InlineKeyboardButton(
        text=localization.get_text(
            "nav.next",
            lang),
             callback_data=f"exchanges_next:{page}"))
        buttons.append(nav_row)

    buttons.append([InlineKeyboardButton(text=localization.get_text(
        "nav.to_main", lang), callback_data="back_to_main")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


@router.callback_query(F.data.startswith("exchanges_prev:"))
async def exchanges_prev_page_handler(
    callback: CallbackQuery,
     state: FSMContext) -> None:
    try:
        user_data = await state.get_data()
        lang = user_data.get("lang", "ua")
        page = int(callback.data.split(":")[1])
        new_page = max(1, page - 1)
        await callback.answer()
        await _display_all_exchanges(callback.message, state, new_page, is_callback=True, lang=lang)
    except Exception as e:
        logger.error(
    f"Помилка в exchanges_prev_page_handler: {e}",
     exc_info=True)


@router.callback_query(F.data.startswith("exchanges_next:"))
async def exchanges_next_page_handler(
    callback: CallbackQuery,
     state: FSMContext) -> None:
    try:
        user_data = await state.get_data()
        lang = user_data.get("lang", "ua")
        page = int(callback.data.split(":")[1])
        new_page = page + 1
        await callback.answer()
        await _display_all_exchanges(callback.message, state, new_page, is_callback=True, lang=lang)
    except Exception as e:
        logger.error(
    f"Помилка в exchanges_next_page_handler: {e}",
     exc_info=True)


@router.callback_query(F.data == "advanced_search")
async def advanced_search_handler(
    callback: CallbackQuery,
     state: FSMContext) -> None:
    user_data = await state.get_data()
    lang = user_data.get("lang", "ua")
    await callback.answer()
    await _display_advanced_search(callback.message, state, is_callback=True, lang=lang)


async def _display_advanced_search(message, state: FSMContext, is_callback: bool = False, lang: str = "ua") -> None:
    try:
        await state.update_data(current_page="advanced_search")
        filters = await state.get_data()

        all_products_txt = localization.get_text("search.product.all", lang)
        all_exchanges_txt = localization.get_text("search.exchange.all", lang)
        all_types_txt = localization.get_text("search.type.all", lang)

        selected_product = filters.get("search_product", all_products_txt)
        selected_exchange = filters.get("search_exchange", all_exchanges_txt)
        selected_type = filters.get("search_type", all_types_txt)

        text = f"🔍 <b>{localization.get_text('search.title', lang)}</b>\n\n"
        text += f"{localization.get_text('search.product.label', lang)}: {selected_product}\n"
        text += f"{localization.get_text('search.exchange.label', lang)}: {selected_exchange}\n"
        text += f"{localization.get_text('search.type.label', lang)}: {selected_type}\n\n"

        keyboard = _create_advanced_search_keyboard(selected_product, selected_exchange, selected_type, lang)

        if is_callback:
            await message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
        else:
            await message.answer(text, reply_markup=keyboard, parse_mode="HTML")
    except Exception as e:
        logger.error(f"Помилка відображення розширеного пошуку: {e}", exc_info=True)

def _create_advanced_search_keyboard(
    product: str,
    exchange: str,
    search_type: str,
     lang: str = "ua") -> InlineKeyboardMarkup:
    buttons = []

    # Product Filter
    prod_label = localization.get_text("search.product.label", lang)
    buttons.append([InlineKeyboardButton(
        text=f"{prod_label}: {product}", callback_data="search_filter_product")])

    # Exchange Filter
    exch_label = localization.get_text("search.exchange.label", lang)
    buttons.append([InlineKeyboardButton(
        text=f"{exch_label}: {exchange}", callback_data="search_filter_exchange")])

    # Type Filter
    type_label = localization.get_text("search.type.label", lang)
    buttons.append([InlineKeyboardButton(
        text=f"{type_label}: {search_type}", callback_data="search_filter_type")])

    # Action Buttons
    buttons.append([
        InlineKeyboardButton(
    text=localization.get_text(
        "search.button.search",
        lang),
         callback_data="search_execute"),
        InlineKeyboardButton(
    text=localization.get_text(
        "search.button.reset",
        lang),
         callback_data="search_reset")
    ])

    buttons.append([InlineKeyboardButton(text=localization.get_text(
        "nav.to_main", lang), callback_data="back_to_main")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


@router.callback_query(F.data == "search_filter_product")
async def search_filter_product_handler(
    callback: CallbackQuery,
     state: FSMContext) -> None:
    try:
        user_data = await state.get_data()
        lang = user_data.get("lang", "ua")
        await callback.answer()

        current_product = user_data.get(
    "search_product", localization.get_text(
        "search.product.all", lang))
        products = [
    localization.get_text(
        "search.product.all",
        lang),
        "BTC",
        "ETH",
        "SOL",
        "USDT",
        "USDC",
        "BNB",
        "ADA",
        "DOT",
        "XRP",
        "AVAX",
        "MATIC",
        localization.get_text(
            "search.manual_input",
             lang)]

        buttons = []
        for product in products:
            text = f"✓ {product}" if product == current_product else product
            cb_data = f"search_select_product:{product}" if product != localization.get_text(
                "search.manual_input", lang) else "search_select_product:MANUAL"
            buttons.append([InlineKeyboardButton(
                text=text, callback_data=cb_data)])

        buttons.append([InlineKeyboardButton(text=localization.get_text(
            "nav.back_to_list", lang), callback_data="back_to_advanced_search")])
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

        await callback.message.edit_text(f"🪙 <b>{localization.get_text('search.product.label', lang)}</b>", reply_markup=keyboard, parse_mode="HTML")
    except Exception as e:
        logger.error(
    f"Помилка в search_filter_product_handler: {e}",
     exc_info=True)


@router.callback_query(F.data.startswith("search_select_product:"))
async def search_select_product_handler(
    callback: CallbackQuery,
    state: FSMContext) -> None:
    try:
        user_data = await state.get_data()
        lang = user_data.get("lang", "ua")
        product = callback.data.split(":", 1)[1]

        if product == "MANUAL":
            await state.set_state(SearchStates.waiting_product_input)
            await callback.answer()
            keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=localization.get_text("nav.back_to_list", lang), callback_data="search_cancel_manual_input")]])
            await callback.message.edit_text(localization.get_text("search.manual_prompt", lang), reply_markup=keyboard, parse_mode="HTML")
        else:
            await state.update_data(search_product=product)
            await callback.answer(localization.get_text("success.product_selected", lang, product=product))
            await _display_advanced_search(callback.message, state, is_callback=True, lang=lang)
    except Exception as e:
        logger.error(f"Помилка в search_select_product_handler: {e}", exc_info=True)


@router.callback_query(F.data == "search_filter_exchange")
async def search_filter_exchange_handler(callback: CallbackQuery, state: FSMContext) -> None:
    try:
        user_data = await state.get_data()
        lang = user_data.get("lang", "ua")
        await callback.answer()

        current_exchange = user_data.get("search_exchange", localization.get_text("search.exchange.all", lang))
        exchanges = [localization.get_text("search.exchange.all", lang), "Binance", "Bybit", "OKX", "MEXC", "BitMart", "gate", "Bitget", "Kraken", "KuCoin", "HTX"]

        buttons = []
        for exchange in exchanges:
            text = f"✓ {exchange}" if exchange == current_exchange else exchange
            # Use simplified exchange name in callback to avoid issues? Or map back.
            # For now using full name.
            buttons.append([InlineKeyboardButton(text=text, callback_data=f"search_select_exchange:{exchange}")])

        buttons.append([InlineKeyboardButton(text=localization.get_text("nav.back_to_list", lang), callback_data="back_to_advanced_search")])
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

        await callback.message.edit_text(f"🏦 <b>{localization.get_text('search.exchange.label', lang)}</b>", reply_markup=keyboard, parse_mode="HTML")
    except Exception as e:
        logger.error(f"Помилка в search_filter_exchange_handler: {e}", exc_info=True)


@router.callback_query(F.data.startswith("search_select_exchange:"))
async def search_select_exchange_handler(callback: CallbackQuery, state: FSMContext) -> None:
    try:
        user_data = await state.get_data()
        lang = user_data.get("lang", "ua")
        exchange = callback.data.split(":", 1)[1]
        await state.update_data(search_exchange=exchange)
        await callback.answer()
        await _display_advanced_search(callback.message, state, is_callback=True, lang=lang)
    except Exception as e:
        logger.error(f"Помилка в search_select_exchange_handler: {e}", exc_info=True)


@router.callback_query(F.data == "search_filter_type")
async def search_filter_type_handler(callback: CallbackQuery, state: FSMContext) -> None:
    try:
        user_data = await state.get_data()
        lang = user_data.get("lang", "ua")
        await callback.answer()

        current_type = user_data.get("search_type", localization.get_text("search.type.all", lang))
        types = [localization.get_text("search.type.all", lang), "Flexible", "Locked"]

        buttons = []
        for t in types:
            text = f"✓ {t}" if t == current_type else t
            buttons.append([InlineKeyboardButton(text=text, callback_data=f"search_select_type:{t}")])

        buttons.append([InlineKeyboardButton(text=localization.get_text("nav.back_to_list", lang), callback_data="back_to_advanced_search")])
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

        await callback.message.edit_text(f"⚡ <b>{localization.get_text('search.type.label', lang)}</b>", reply_markup=keyboard, parse_mode="HTML")
    except Exception as e:
        logger.error(f"Помилка в search_filter_type_handler: {e}", exc_info=True)


@router.callback_query(F.data.startswith("search_select_type:"))
async def search_select_type_handler(callback: CallbackQuery, state: FSMContext) -> None:
    try:
        user_data = await state.get_data()
        lang = user_data.get("lang", "ua")
        search_type = callback.data.split(":", 1)[1]
        await state.update_data(search_type=search_type)
        await callback.answer()
        await _display_advanced_search(callback.message, state, is_callback=True, lang=lang)
    except Exception as e:
        logger.error(f"Помилка в search_select_type_handler: {e}", exc_info=True)


@router.callback_query(F.data == "back_to_advanced_search")
async def back_to_advanced_search_handler(callback: CallbackQuery, state: FSMContext) -> None:
    try:
        user_data = await state.get_data()
        lang = user_data.get("lang", "ua")
        await callback.answer()
        await _display_advanced_search(callback.message, state, is_callback=True, lang=lang)
    except Exception as e:
        logger.error(f"Помилка в back_to_advanced_search_handler: {e}", exc_info=True)


@router.callback_query(F.data == "search_reset")
async def search_reset_handler(callback: CallbackQuery, state: FSMContext) -> None:
    try:
        user_data = await state.get_data()
        lang = user_data.get("lang", "ua")
        await state.update_data(
            search_product=localization.get_text("search.product.all", lang),
            search_exchange=localization.get_text("search.exchange.all", lang),
            search_type=localization.get_text("search.type.all", lang),
        )
        await callback.answer(localization.get_text("menu.reset", lang))
        await _display_advanced_search(callback.message, state, is_callback=True, lang=lang)
    except Exception as e:
        logger.error(f"Помилка в search_reset_handler: {e}", exc_info=True)


@router.callback_query(F.data == "search_execute")
async def search_execute_handler(callback: CallbackQuery, state: FSMContext) -> None:
    try:
        user_data = await state.get_data()
        lang = user_data.get("lang", "ua")
        await callback.answer(localization.get_text("loading.search", lang))

        data = await state.get_data()
        product = data.get("search_product", localization.get_text("search.product.all", lang))
        exchange = data.get("search_exchange", localization.get_text("search.exchange.all", lang))
        search_type = data.get("search_type", localization.get_text("search.type.all", lang))

        await _execute_advanced_search(
            callback.message, state, product, exchange, search_type, is_callback=True, lang=lang
        )
    except Exception as e:
        logger.error(f"Помилка в search_execute_handler: {e}", exc_info=True)


@router.message(SearchStates.waiting_product_input, F.text)
async def process_manual_product_input(message: Message, state: FSMContext) -> None:
    try:
        user_data = await state.get_data()
        lang = user_data.get("lang", "ua")
        product_input = message.text.strip().upper()

        if not product_input or len(product_input) > 20:
            await message.answer(localization.get_text("error.invalid_product", lang))
            return

        await state.update_data(search_product=product_input)
        await state.set_state(None)
        await message.answer(localization.get_text("success.product_selected", lang, product=product_input))
        await _display_advanced_search(message, state, is_callback=False, lang=lang)
    except Exception as e:
        logger.error(f"Помилка в process_manual_product_input: {e}", exc_info=True)


@router.callback_query(F.data == "search_cancel_manual_input")
async def cancel_manual_product_input(callback: CallbackQuery, state: FSMContext) -> None:
    user_data = await state.get_data()
    lang = user_data.get("lang", "ua")
    await state.set_state(None)
    await callback.answer()
    await _display_advanced_search(callback.message, state, is_callback=True, lang=lang)


async def _execute_advanced_search(message, state: FSMContext, product: str, exchange: str, search_type: str, is_callback: bool = False, lang: str = "ua") -> None:
    # Map localized string back to API values if needed.
    # For simplicity assuming product symbol is what we want unless it's "All Products" localized.

    all_prod = localization.get_text("search.product.all", lang)
    all_exch = localization.get_text("search.exchange.all", lang)
    # all_type = localization.get_text("search.type.all", lang) # Not used for filtering per se, just logic

    api_client = APIClient()
    try:
        symbol_filter = None if product == all_prod else product.upper()
        exchange_filter = None if exchange == all_exch else exchange

        # ... API calls logic similar to original but with localized error handling ...
        # For brevity using get_all_products directly

        # Simplification: assuming Flexible/Locked mapping
        lock_days = 0 if search_type == "Flexible" else None

        data = await api_client.get_all_products(limit=1000, symbol=symbol_filter, provider=exchange_filter, lock_period_days=lock_days)

        products = data.get("data", []) if data.get("success") else []

        if search_type == "Locked":
            products = [p for p in products if p.get("lock_period_days", 0) > 0]

        text = f"🔍 <b>{localization.get_text('search.title', lang)}</b>\n\n"
        text += f"{localization.get_text('search.product.label', lang)}: {product}\n"
        text += f"{localization.get_text('search.exchange.label', lang)}: {exchange}\n"

        if not products:
            text += localization.get_text("error.nothing_found", lang)
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=localization.get_text("nav.back_to_list", lang), callback_data="back_to_advanced_search")],
                [InlineKeyboardButton(text=localization.get_text("nav.to_main", lang), callback_data="back_to_main")]
            ])
        else:
            # Formatting table
            from bot.utils.formatters import format_all_products_table
            # Assuming formatters update in next step, passing lang if I update it
            table_text = format_all_products_table(products[:50], page=1, items_per_page=50, total_products=len(products)) # TODO: Pass lang
            text += table_text

            # Store results
            await state.update_data(search_results=products[:500]) # limit storage

            buttons = []
            buttons.append([InlineKeyboardButton(text=localization.get_text("nav.back_to_list", lang), callback_data="back_to_advanced_search")])
            buttons.append([InlineKeyboardButton(text=localization.get_text("nav.to_main", lang), callback_data="back_to_main")])
            keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

        if is_callback:
            await message.edit_text(text, reply_markup=keyboard, parse_mode="HTML", link_preview_options=LinkPreviewOptions(is_disabled=True))
        else:
            await message.answer(text, reply_markup=keyboard, parse_mode="HTML", link_preview_options=LinkPreviewOptions(is_disabled=True))

    finally:
        await api_client.close()

@router.message(Command("clear_cache"))
async def clear_cache_command(message: Message) -> None:
    # Admin command, can stay in UA/English
    pass
