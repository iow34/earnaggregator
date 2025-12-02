"""
Обробник продуктів конкретної біржі (Сторінка 2).

Відображає:
- Всі продукти обраної біржі
- Фільтри (продукт, тип, APY)
- Таблицю в monospace форматі
- Пагінацію
"""

from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, LinkPreviewOptions
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext
from typing import List, Dict, Optional
import re

from bot.services.api_client import APIClient
from bot.services.referral_link_generator import referral_link_generator
from bot.keyboards.filters import filter_keyboard, create_exchange_filters_keyboard
from bot.keyboards.navigation import exchange_menu_keyboard, back_button_keyboard
from bot.utils.pagination import Paginator
from bot.utils.formatters import format_exchange_product_table
from bot.utils.logger import logger
from bot.services.filter_state import FilterStateManager
from bot.utils.loading_indicator import LoadingIndicator
from bot.config import settings
from bot.localization import localization
from bot.db.database import db_manager
from bot.db.crud import get_or_create_user


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

router = Router(name="exchange_products_handler")
async def _resolve_user_language(user, state: FSMContext) -> str:
    """Ensure we know user language either from state or DB."""
    data = await state.get_data()
    lang = data.get("lang") or data.get("language")
    if lang in {"ua", "ru", "en"}:
        return lang

    async with db_manager.get_session() as session:
        db_user = await get_or_create_user(
            session=session,
            telegram_id=user.id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name,
        )
        lang = db_user.language or "ua"

    await state.update_data(lang=lang)
    return lang


# Реферальні посилання завантажуються з config (settings)


@router.callback_query(F.data.startswith("show_all:"))
async def show_exchange_products(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Показати всі продукти конкретної біржі.

    Args:
        callback: Callback query
        state: FSM контекст
    """
    # Get language from state
    data = await state.get_data()
    lang = data.get("lang")
    if lang not in {"ua", "ru", "en"}:
        lang = await _resolve_user_language(callback.from_user, state)

    try:
        # Отримати назву біржі з callback
        provider = callback.data.split(":")[1]

        await callback.answer(localization.get_text("messages.loading_products", lang))

        # Скинути фільтри при переході на сторінку конкретної біржі
        from bot.services.filter_state import FilterStateManager
        await FilterStateManager.reset_filters_on_page_change(state, "exchange_products")

        # Ініціалізувати стан
        await state.update_data(
            current_page="exchange_products",
            provider=provider,
            page=1
        )

        # Зберегти навігаційний стан
        await FilterStateManager.save_navigation_state(
            state,
            current_page="exchange_products",
            provider=provider,
            page=1
        )

        # Завантажити та показати продукти
        await _display_exchange_products(callback.message, state, provider, is_callback=True, lang=lang)

    except Exception as e:
        logger.error(f"Помилка в show_exchange_products: {e}", exc_info=True)
        await callback.answer(localization.get_error_text("error.data_unavailable", lang), show_alert=True)


async def _display_exchange_products(
    message,
    state: FSMContext,
    provider: str,
    page: int = 1,
    is_callback: bool = False,
    lang: str = "ua"
) -> None:
    """
    Відобразити продукти біржі з фільтрами та пагінацією.
    
    Args:
        message: Повідомлення для редагування
        state: FSM контекст
        provider: Назва біржі
        page: Номер сторінки
        is_callback: Чи це callback
        lang: Код мови
    """
    try:
        api_client = APIClient()
        
        # Зберегти provider в state для майбутніх використань (наприклад, кнопка "Назад" в меню сортування)
        await state.update_data(provider=provider)

        # Зберегти навігаційний стан
        await FilterStateManager.save_navigation_state(
            state,
            current_page="exchange_products",
            provider=provider
        )
        
        # Отримати фільтри
        filters = await FilterStateManager.get_current_filters(state)

        # Єдина стратегія отримання даних для всіх бірж
        sort_by = filters.get("sort_by", "popularity")

        # Стратегія отримання даних залежно від типу сортування
        if sort_by == "popularity":
            # Спробуємо отримати популярні продукти з сервера
            # Для HTX зменшуємо limit щоб уникнути таймаутів
            limit = 50 if provider.lower() == "htx" else 1000
            logger.info(f"🔥 Отримуємо популярні продукти {provider} з сервера (limit={limit})")
            data = await api_client.get_exchanges_popular(exchange=provider.lower(), limit=limit)

            # Якщо популярних продуктів недостатньо, fallback на звичайні продукти
            # Для невеликих бірж (як MEXC, HTX) зменшуємо поріг до 3 продуктів
            min_popular_threshold = 3 if provider.lower() in ["mexc", "htx"] else 10

            if not data.get("success") or len(data.get("data", [])) < min_popular_threshold:
                logger.info(f"⚠️ Популярних продуктів {provider} недостатньо ({len(data.get('data', []))} < {min_popular_threshold}), використовуємо звичайні продукти з повідомленням про недоступність популярності")
                limit = 50 if provider.lower() == "htx" else 1000
                data = await api_client.get_exchanges(exchange=provider, limit=limit)
                # Залишаємо sort_by="popularity" але додаємо прапор що це fallback
                filters["popularity_fallback"] = True

        elif sort_by in ["apy_desc", "apy_asc"]:
            # Для APY сортування завжди використовуємо звичайний ендпоінт
            limit = 50 if provider.lower() == "htx" else 1000
            logger.info(f"📊 Отримуємо продукти {provider} для локального APY сортування ({sort_by}, limit={limit})")
            data = await api_client.get_exchanges(exchange=provider, limit=limit)

        else:
            # Невідомий тип сортування - fallback на популярність
            logger.warning(f"⚠️ Невідомий тип сортування {sort_by}, використовуємо популярність")
            limit = 50 if provider.lower() == "htx" else 1000
            data = await api_client.get_exchanges_popular(exchange=provider.lower(), limit=limit)
            filters["sort_by"] = "popularity"
        
        if not data.get("success"):
            display_name = _format_exchange_display_name(provider)
            error_text = localization.get_error_text("error.data_unavailable_for_exchange", lang, exchange=display_name)
            if is_callback:
                await message.edit_text(
                    error_text,
                    reply_markup=back_button_keyboard(lang=lang)
                )
            else:
                await message.answer(
                    error_text,
                    reply_markup=back_button_keyboard(lang=lang)
                )
            await api_client.close()
            return
        
        products = data.get("data", [])
        
        # Застосувати локальні фільтри
        products = _apply_local_filters(products, filters)
        
        # Блок 1: Заголовок з реферальним посиланням через redirect server (page=2 - продукти біржі)
        # КРИТИЧНА ПЕРЕВІРКА: Для telegram_id=0 використовуємо прямі посилання без трекінгу
        telegram_id = message.from_user.id if hasattr(message, 'from_user') else message.chat.id
        
        try:
            if telegram_id > 0:
                # Реальний користувач - генеруємо трекінгове посилання
                referral_url = await referral_link_generator.generate_link(
                    telegram_id=telegram_id,
                    exchange=provider.lower(),
                    page="2"  # Сторінка 2 - продукти біржі
                )
            else:
                # Для telegram_id=0 використовуємо прямі реферальні посилання
                logger.debug(f"ℹ️ Telegram ID=0 для {provider}, використовуємо прямі посилання")
                referral_url = settings.referral_urls.get(provider.lower(), "https://www.binance.com")
        except Exception as e:
            logger.error(f"❌ Помилка генерації трекінгового посилання для {provider}: {e}")
            referral_url = settings.referral_urls.get(provider.lower(), "https://www.binance.com")
        
        # Перевірка валідності URL перед вставкою в HTML
        if not referral_url or referral_url == "" or referral_url == "#" or not referral_url.startswith('http'):
            logger.warning(f"⚠️ Трекінгове посилання некоректне для {provider}, використовуємо fallback")
            referral_url = settings.referral_urls.get(provider.lower(), "https://www.binance.com")
        
        # КРИТИЧНА ПЕРЕВІРКА: якщо URL містить localhost/127.0.0.1/yield-api - Telegram не може перейти на нього
        # Використовуємо прямі реферальні посилання бірж замість трекінгових для локальної розробки
        if referral_url and ('localhost' in referral_url or '127.0.0.1' in referral_url or 'yield-api' in referral_url):
            logger.warning(
                f"⚠️ URL містить localhost/yield-api для {provider}, використовуємо прямі реферальні посилання "
                f"(Telegram не може перейти на внутрішні адреси Docker)"
            )
            referral_url = settings.referral_urls.get(provider.lower(), "https://www.binance.com")
            # Додаткова перевірка fallback
            if not referral_url or referral_url == "#" or not referral_url.startswith('http'):
                referral_url = "https://www.binance.com"
        
        # Перевірка валідності URL
        if not referral_url or not referral_url.startswith('http'):
            logger.warning(f"⚠️ Трекінгове посилання некоректне для {provider}, використовуємо fallback з .env")
            # Fallback на статичне трекінгове посилання з .env для сторінки 2
            fallback_tracking = settings.get_tracking_link(provider.lower(), "2")
            if fallback_tracking:
                # Перевіряємо чи fallback також не містить localhost/yield-api
                if 'localhost' not in fallback_tracking and '127.0.0.1' not in fallback_tracking and 'yield-api' not in fallback_tracking:
                    referral_url = fallback_tracking
                else:
                    # Якщо fallback містить localhost/yield-api - використовуємо прямі реферальні посилання
                    referral_url = settings.referral_urls.get(provider.lower(), "https://www.binance.com")
            else:
                # Якщо немає fallback - використовуємо прямі реферальні посилання
                referral_url = settings.referral_urls.get(provider.lower(), "https://www.binance.com")
        
        # Екрануємо & в URL для правильного HTML форматування в Telegram
        escaped_url = referral_url.replace('&', '&amp;')
        
        # Localized title
        display_name = _format_exchange_display_name(provider)
        title = localization.get_text(
            "section.exchange_products_title",
            lang,
            exchange=display_name,
            url=escaped_url
        )
        if title == "section.exchange_products_title":
            title = f"🏦 <b>Всі продукти біржі <a href=\"{escaped_url}\">{display_name}</a></b>"
        text = f"{title}\n\n"
        
        # Блок 2: Активні фільтри
        filters_display = await FilterStateManager.get_filters_display(state, lang=lang)
        # FilterStateManager is in bot/services/filter_state.py. I should check it later.
        text += filters_display + "\n\n"

        # Блок 2.5: Повідомлення про fallback сортування (якщо популярність недоступна)
        if filters.get("popularity_fallback") and sort_by == "popularity":
            text += f"⚠️ {localization.get_text('messages.popularity_sort_unavailable', lang)}\n\n"
        
        # Блок 3: Таблиця з продуктами
        if not products:
            text += localization.get_text("messages.nothing_found", lang)
            if is_callback:
                await message.edit_text(
                    text,
                    reply_markup=create_exchange_filters_keyboard(provider, filters, lang=lang), # Need to update filters keyboard to accept lang
                    parse_mode="HTML"
                )
            else:
                await message.answer(
                    text,
                    reply_markup=create_exchange_filters_keyboard(provider, filters, lang=lang),
                    parse_mode="HTML"
                )
            await api_client.close()
            return
        
        # Пагінація - збільшено до 50 продуктів на сторінку
        paginator = Paginator(products, items_per_page=50)
        page_products = paginator.get_page(page)

        # Форматування таблиці (пагінація вже зроблена вище)
        # format_exchange_product_table needs lang!
        table_text = format_exchange_product_table(page_products, page, 50, len(products), lang=lang)
        text += table_text
        
        # Блок 4: Підсумок та пагінація
        summary = localization.get_text(
            "table.summary.shown",
            lang,
            shown=len(page_products),
            total=len(products)
        )
        text += f"\n\n{summary}"
        
        # Створити клавіатуру
        keyboard_buttons = []
        
        # Додати фільтри
        keyboard_buttons.extend(create_exchange_filters_keyboard(provider, filters, lang=lang).inline_keyboard)
        
        # Додати пагінацію
        if paginator.total_pages > 1:
            pagination_kb = paginator.get_navigation_keyboard(page, f"exchange_{provider}", lang=lang) # Update Paginator to accept lang
            keyboard_buttons.extend(pagination_kb.inline_keyboard)
        
        # Додати кнопку назад
        from aiogram.types import InlineKeyboardButton
        keyboard_buttons.append([
            InlineKeyboardButton(
                text=localization.get_text("nav.to_main", lang),
                callback_data="back_to_main"
            )
        ])
        
        from aiogram.types import InlineKeyboardMarkup
        keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
        
        if is_callback:
            await message.edit_text(
                text,
                reply_markup=keyboard,
                parse_mode="HTML",
                link_preview_options=LinkPreviewOptions(is_disabled=True)  # Вимикаємо прев'ю та банер
            )
        else:
            await message.answer(
                text,
                reply_markup=keyboard,
                parse_mode="HTML",
                link_preview_options=LinkPreviewOptions(is_disabled=True)  # Вимикаємо прев'ю та банер
            )
        
        await api_client.close()
        
    except Exception as e:
        logger.error(f"Помилка відображення продуктів: {e}", exc_info=True)
        error_msg = localization.get_error_text("error.display_results_error", lang)
        if is_callback:
            await message.edit_text(
                error_msg,
                reply_markup=back_button_keyboard(lang=lang)
            )
        else:
            await message.answer(
                error_msg,
                reply_markup=back_button_keyboard(lang=lang)
            )


# Стара функція _format_products_table видалена - замінена на format_exchange_product_table з utils.formatters


def _apply_local_filters(products: List[Dict], filters: Dict) -> List[Dict]:
    """
    Застосувати фільтри до продуктів локально.
    
    Args:
        products: Список продуктів
        filters: Словник з фільтрами
        
    Returns:
        Відфільтрований список продуктів
    """
    filtered = products
    
    # Фільтр по продукту (символу)
    if filters.get("product"):
        filtered = [p for p in filtered if p.get("symbol") == filters["product"].upper()]
    
    # Фільтр по типу - враховує як product_type, так і lock_period_days як fallback
    if filters.get("type"):
        if filters["type"] == "flexible":
            def is_flexible_product(p):
                # Спочатку перевіряємо поле product_type
                product_type = p.get("product_type")
                if product_type and isinstance(product_type, str):
                    product_type_lower = product_type.lower()
                    if any(term in product_type_lower for term in ["flexible", "simpleflexible"]):
                        return True
                # Fallback: перевіряємо lock_period_days
                return p.get("lock_period_days", 0) == 0
            filtered = [p for p in filtered if is_flexible_product(p)]

        elif filters["type"] == "locked":
            def is_locked_product(p):
                # Спочатку перевіряємо поле product_type
                product_type = p.get("product_type")
                if product_type and isinstance(product_type, str):
                    product_type_lower = product_type.lower()
                    if any(term in product_type_lower for term in ["locked", "fixed", "bonded"]):
                        return True
                # Fallback: перевіряємо lock_period_days
                return p.get("lock_period_days", 0) > 0
            filtered = [p for p in filtered if is_locked_product(p)]
    
    # Фільтр по APY діапазону
    if filters.get("apy_min"):
        filtered = [p for p in filtered if p.get("apy", 0) >= filters["apy_min"]]
    if filters.get("apy_max"):
        filtered = [p for p in filtered if p.get("apy", 0) <= filters["apy_max"]]
    
    # Сортування
    sort_by = filters.get("sort_by", "apy_desc")
    if sort_by == "popularity":
        # Якщо це fallback режим популярності (недоступна), сортуємо за APY
        if filters.get("popularity_fallback"):
            filtered.sort(key=lambda x: x.get("apy", 0), reverse=True)
        # Якщо популярність доступна, сортування вже зроблено в API
    elif sort_by == "apy_desc":
        filtered.sort(key=lambda x: x.get("apy", 0), reverse=True)
    elif sort_by == "apy_asc":
        filtered.sort(key=lambda x: x.get("apy", 0))
    
    return filtered


@router.callback_query(F.data.startswith("exchange_") & F.data.contains("_prev:"))
async def prev_page_handler(callback: CallbackQuery, state: FSMContext) -> None:
    """Обробник попередньої сторінки."""
    # Get language from state
    data = await state.get_data()
    lang = data.get("lang", "ua")
    
    try:
        # Розпарсити callback: exchange_{provider}_prev:{page}
        data_parts = callback.data.split("_")
        provider = data_parts[1]  # exchange_binance_prev:2 -> binance
        page_str = callback.data.split(":")[1]
        current_page = int(page_str)
        new_page = current_page - 1

        await state.update_data(page=new_page)
        await callback.answer()
        await _display_exchange_products(callback.message, state, provider, new_page, is_callback=True, lang=lang)
        
    except Exception as e:
        logger.error(f"Помилка в prev_page_handler: {e}", exc_info=True)
        await callback.answer(localization.get_error_text("error.general", lang), show_alert=True)


@router.callback_query(F.data.startswith("exchange_") & F.data.contains("_next:"))
async def next_page_handler(callback: CallbackQuery, state: FSMContext) -> None:
    """Обробник наступної сторінки."""
    # Get language from state
    data = await state.get_data()
    lang = data.get("lang", "ua")
    
    try:
        # Розпарсити callback: exchange_{provider}_next:{page}
        data_parts = callback.data.split("_")
        provider = data_parts[1]  # exchange_binance_next:2 -> binance
        page_str = callback.data.split(":")[1]
        current_page = int(page_str)
        new_page = current_page + 1

        await state.update_data(page=new_page)
        await callback.answer()
        await _display_exchange_products(callback.message, state, provider, new_page, is_callback=True, lang=lang)
        
    except Exception as e:
        logger.error(f"Помилка в next_page_handler: {e}", exc_info=True)
        await callback.answer(localization.get_error_text("error.general", lang), show_alert=True)


@router.callback_query(F.data.startswith("filters:"))
async def show_exchange_filters(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Показати фільтри для конкретної біржі.

    Args:
        callback: Callback query
        state: FSM контекст
    """
    # Get language from state
    data = await state.get_data()
    lang = data.get("lang", "ua")
    
    try:
        # Отримати назву біржі з callback
        provider = callback.data.split(":")[1]

        display_name = _format_exchange_display_name(provider)
        await callback.answer(
            localization.get_text("loading.filters_for_exchange", lang, exchange=display_name)
        )

        # Показати повідомлення з фільтрами
        from bot.keyboards.filters import create_exchange_filters_keyboard

        # Отримати поточні фільтри для відображення стану сортування
        filters = await FilterStateManager.get_current_filters(state)

        display_name = _format_exchange_display_name(provider)
        await callback.message.answer(
            localization.get_text("search.filters_for_exchange_title", lang, exchange=display_name),
            reply_markup=create_exchange_filters_keyboard(provider, filters, lang=lang),
            parse_mode="HTML"
        )

    except Exception as e:
        logger.error(f"Помилка в show_exchange_filters: {e}", exc_info=True)
        await callback.answer(localization.get_error_text("error.general", lang), show_alert=True)


@router.message(F.text.startswith("/all_") & F.text.endswith("_products"))
async def show_all_exchange_products_command(message: Message, state: FSMContext) -> None:
    """
    Обробник команди /all_{exchange}_products для показу всіх продуктів біржі.

    Використовує простий фільтр замість regexp.
    """
    # Get language from state
    data = await state.get_data()
    lang = data.get("lang")
    if lang not in {"ua", "ru", "en"}:
        lang = await _resolve_user_language(message.from_user, state)
    
    try:
        text = message.text.strip()
        logger.info(f"📋 Отримано команду: {text} від користувача {message.from_user.id}")

        # Отримуємо назву біржі з тексту
        if not text.startswith("/all_") or not text.endswith("_products"):
            logger.warning(f"❌ Неправильний формат команди: {text}")
            return

        provider = text[5:-9].lower()  # видаляємо "/all_" і "_products"

        logger.info(f"📋 Обробка команди /all_{provider}_products від користувача {message.from_user.id}")

        # Нормалізуємо назву біржі
        if provider in ["binance", "bnb"]:
            provider = "binance"
        elif provider in ["bybit", "byb"]:
            provider = "bybit"
        elif provider in ["bitmart"]:
            provider = "bitmart"
        elif provider in ["okx"]:
            provider = "okx"
        elif provider in ["mexc"]:
            provider = "mexc"
        elif provider in ["gate"]:
            provider = "gate"
        elif provider in ["bitget"]:
            provider = "bitget"
        elif provider in ["kraken"]:
            provider = "kraken"
        elif provider in ["kucoin"]:
            provider = "kucoin"
        elif provider in ["htx", "huobi"]:
            provider = "htx"
        elif provider in ["nexo"]:
            # Заглушка для Nexo - продукти будуть додані пізніше
            try:
                telegram_id = message.from_user.id if hasattr(message, 'from_user') else message.chat.id
                try:
                    # Завжди використовуємо трекінгові посилання через generate_link
                    referral_url = await referral_link_generator.generate_link(
                        telegram_id=telegram_id,
                        exchange="nexo",
                        page="2"  # Сторінка продуктів біржі
                    )
                except Exception as e:
                    logger.warning(f"⚠️ Помилка генерації трекінгового посилання для nexo: {e}")
                    # Fallback на прямі посилання тільки при критичній помилці
                    from bot.handlers.main_menu import _get_referral_url
                    referral_url = _get_referral_url("nexo")
                
                escaped_url = referral_url.replace('&', '&amp;')
                exchange_link = f'<a href="{escaped_url}">Nexo</a>'
                display_name = _format_exchange_display_name("nexo")
                
                await message.answer(
                    localization.get_text("messages.nexo_coming_soon", lang, exchange=display_name, exchange_link=exchange_link),
                    parse_mode="HTML",
                    link_preview_options=LinkPreviewOptions(is_disabled=True)
                )
            except Exception as e:
                logger.error(f"Помилка показу заглушки для Nexo: {e}", exc_info=True)
                # Fallback на прямі посилання тільки при критичній помилці
                from bot.handlers.main_menu import _get_referral_url
                referral_url = _get_referral_url("nexo")
                escaped_url = referral_url.replace('&', '&amp;')
                exchange_link = f'<a href="{escaped_url}">Nexo</a>'
                display_name = _format_exchange_display_name("nexo")
                await message.answer(
                    localization.get_text("messages.nexo_coming_soon", lang, exchange=display_name, exchange_link=exchange_link),
                    parse_mode="HTML",
                    link_preview_options=LinkPreviewOptions(is_disabled=True)
                )
            return
        else:
            await message.answer(
                f"{localization.get_error_text('error.unknown_exchange', lang, exchange=provider)}\n\n"
                f"{localization.get_text('messages.available_exchanges', lang)}"
            )
            return

        # Скинути фільтри при переході на сторінку конкретної біржі
        from bot.services.filter_state import FilterStateManager
        await FilterStateManager.reset_filters_on_page_change(state, "exchange_products")

        # Встановити поточну сторінку
        await state.update_data(
            current_page="exchange_products",
            provider=provider,
            page=1
        )

        # Використовуємо індикатор завантаження
        display_name = _format_exchange_display_name(provider)
        async with LoadingIndicator(message, localization.get_text("loading.products_for_exchange", lang, exchange=display_name)):
            # Викликаємо функцію відображення продуктів напряму з is_callback=False
            await _display_exchange_products(message, state, provider, is_callback=False, lang=lang)

    except Exception as e:
        logger.error(f"Помилка в show_all_exchange_products_command: {e}", exc_info=True)
        await message.answer(localization.get_error_text("error.general", lang))
