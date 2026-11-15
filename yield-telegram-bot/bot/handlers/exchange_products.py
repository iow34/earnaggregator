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


@router.callback_query(F.data.startswith("show_all:"))
async def show_exchange_products(callback: CallbackQuery, state: FSMContext) -> None:
    # Get language from state
    data = await state.get_data()
    lang = data.get("lang")
    if lang not in {"ua", "ru", "en"}:
        lang = await _resolve_user_language(callback.from_user, state)

    try:
        provider = callback.data.split(":")[1]

        await callback.answer(localization.get_text("messages.loading_products", lang))

        from bot.services.filter_state import FilterStateManager

        await FilterStateManager.reset_filters_on_page_change(state, "exchange_products")

        await state.update_data(current_page="exchange_products", provider=provider, page=1)

        await FilterStateManager.save_navigation_state(
            state, current_page="exchange_products", provider=provider, page=1
        )

        await _display_exchange_products(
            callback.message, state, provider, is_callback=True, lang=lang
        )

    except Exception as e:
        logger.error(f"Помилка в show_exchange_products: {e}", exc_info=True)
        await callback.answer(
            localization.get_error_text("error.data_unavailable", lang), show_alert=True
        )


async def _display_exchange_products(
    message,
    state: FSMContext,
    provider: str,
    page: int = 1,
    is_callback: bool = False,
    lang: str = "ua",
) -> None:
    try:
        api_client = APIClient()

        await state.update_data(provider=provider)

        await FilterStateManager.save_navigation_state(
            state, current_page="exchange_products", provider=provider
        )

        filters = await FilterStateManager.get_current_filters(state)

        sort_by = filters.get("sort_by", "popularity")

        if provider.lower() == "htx":
            limit = 1000
            logger.info(f"🔥 Отримуємо HTX продукти з бази даних (limit={limit})")

            if sort_by == "popularity":
                data = await api_client.get_exchanges_popular(exchange="htx", limit=limit)
                if not data.get("success") or len(data.get("data", [])) < 3:
                    logger.info(
                        f"⚠️ Популярних HTX продуктів недостатньо, використовуємо звичайні продукти з БД"
                    )
                    data = await api_client.get_htx_products_from_db(limit=limit)
                    filters["popularity_fallback"] = True
            else:
                logger.info(f"📊 Отримуємо HTX продукти для сортування ({sort_by}, limit={limit})")
                data = await api_client.get_htx_products_from_db(limit=limit)

        elif sort_by == "popularity":
            limit = 1000
            logger.info(f"🔥 Отримуємо популярні продукти {provider} з сервера (limit={limit})")
            data = await api_client.get_exchanges_popular(exchange=provider.lower(), limit=limit)

            min_popular_threshold = 10

            if not data.get("success") or len(data.get("data", [])) < min_popular_threshold:
                logger.info(
                    f"⚠️ Популярних продуктів {provider} недостатньо ({len(data.get('data', []))} < {min_popular_threshold}), використовуємо звичайні продукти з повідомленням про недоступність популярності"
                )
                limit = 1000
                data = await api_client.get_exchanges(exchange=provider, limit=limit)

                filters["popularity_fallback"] = True

        elif sort_by in ["apy_desc", "apy_asc"]:
            limit = 1000
            logger.info(
                f"📊 Отримуємо продукти {provider} для локального APY сортування ({sort_by}, limit={limit})"
            )
            data = await api_client.get_exchanges(exchange=provider, limit=limit)

        else:
            logger.warning(f"⚠️ Невідомий тип сортування {sort_by}, використовуємо популярність")
            limit = 1000
            data = await api_client.get_exchanges_popular(exchange=provider.lower(), limit=limit)
            filters["sort_by"] = "popularity"

        if not data.get("success"):
            display_name = _format_exchange_display_name(provider)
            error_text = localization.get_error_text(
                "error.data_unavailable_for_exchange", lang, exchange=display_name
            )
            if is_callback:
                await message.edit_text(error_text, reply_markup=back_button_keyboard(lang=lang))
            else:
                await message.answer(error_text, reply_markup=back_button_keyboard(lang=lang))
            await api_client.close()
            return

        products = data.get("data", [])

        products = _apply_local_filters(products, filters)

        telegram_id = message.from_user.id if hasattr(message, "from_user") else message.chat.id

        try:
            if telegram_id > 0:
                referral_url = await referral_link_generator.generate_link(
                    telegram_id=telegram_id, exchange=provider.lower(), page="2"
                )
            else:
                logger.debug(f"ℹ️ Telegram ID=0 для {provider}, використовуємо прямі посилання")
                referral_url = settings.referral_urls.get(
                    provider.lower(), "https://www.binance.com"
                )
        except Exception as e:
            logger.error(f"❌ Помилка генерації трекінгового посилання для {provider}: {e}")
            referral_url = settings.referral_urls.get(provider.lower(), "https://www.binance.com")

        if (
            not referral_url
            or referral_url == ""
            or referral_url == "#"
            or not referral_url.startswith("http")
        ):
            logger.warning(
                f"⚠️ Трекінгове посилання некоректне для {provider}, використовуємо fallback"
            )
            referral_url = settings.referral_urls.get(provider.lower(), "https://www.binance.com")

        if referral_url and (
            "localhost" in referral_url
            or "127.0.0.1" in referral_url
            or "yield-api" in referral_url
        ):
            logger.warning(
                f"⚠️ URL містить localhost/yield-api для {provider}, використовуємо прямі реферальні посилання "
                f"(Telegram не може перейти на внутрішні адреси Docker)"
            )
            referral_url = settings.referral_urls.get(provider.lower(), "https://www.binance.com")

            if not referral_url or referral_url == "#" or not referral_url.startswith("http"):
                referral_url = "https://www.binance.com"

        if not referral_url or not referral_url.startswith("http"):
            logger.warning(
                f"⚠️ Трекінгове посилання некоректне для {provider}, використовуємо fallback з .env"
            )

            fallback_tracking = settings.get_tracking_link(provider.lower(), "2")
            if fallback_tracking:
                if (
                    "localhost" not in fallback_tracking
                    and "127.0.0.1" not in fallback_tracking
                    and "yield-api" not in fallback_tracking
                ):
                    referral_url = fallback_tracking
                else:
                    referral_url = settings.referral_urls.get(
                        provider.lower(), "https://www.binance.com"
                    )
            else:
                referral_url = settings.referral_urls.get(
                    provider.lower(), "https://www.binance.com"
                )

        escaped_url = referral_url.replace("&", "&amp;")

        # Localized title
        display_name = _format_exchange_display_name(provider)
        title = localization.get_text(
            "section.exchange_products_title", lang, exchange=display_name, url=escaped_url
        )
        if title == "section.exchange_products_title":
            title = f'🏦 <b>Всі продукти біржі <a href="{escaped_url}">{display_name}</a></b>'
        text = f"{title}\n\n"

        filters_display = await FilterStateManager.get_filters_display(state, lang=lang)
        # FilterStateManager is in bot/services/filter_state.py. I should check it later.
        text += filters_display + "\n\n"

        if filters.get("popularity_fallback") and sort_by == "popularity":
            text += f"⚠️ {localization.get_text('messages.popularity_sort_unavailable', lang)}\n\n"

        if not products:
            text += localization.get_text("messages.nothing_found", lang)
            if is_callback:
                await message.edit_text(
                    text,
                    reply_markup=create_exchange_filters_keyboard(
                        provider, filters, lang=lang
                    ),  # Need to update filters keyboard to accept lang
                    parse_mode="HTML",
                )
            else:
                await message.answer(
                    text,
                    reply_markup=create_exchange_filters_keyboard(provider, filters, lang=lang),
                    parse_mode="HTML",
                )
            await api_client.close()
            return

        items_per_page = 50

        paginator = Paginator(products, items_per_page=items_per_page)
        page_products = paginator.get_page(page)

        # format_exchange_product_table needs lang!
        table_text = format_exchange_product_table(
            page_products, page, items_per_page, len(products), lang=lang
        )
        text += table_text

        summary = localization.get_text(
            "table.summary.shown", lang, shown=len(page_products), total=len(products)
        )
        text += f"\n\n{summary}"

        keyboard_buttons = []

        keyboard_buttons.extend(
            create_exchange_filters_keyboard(provider, filters, lang=lang).inline_keyboard
        )

        if paginator.total_pages > 1:
            pagination_kb = paginator.get_navigation_keyboard(
                page, f"exchange_{provider}", lang=lang
            )  # Update Paginator to accept lang
            keyboard_buttons.extend(pagination_kb.inline_keyboard)

        from aiogram.types import InlineKeyboardButton

        keyboard_buttons.append(
            [
                InlineKeyboardButton(
                    text=localization.get_text("nav.to_main", lang), callback_data="back_to_main"
                )
            ]
        )

        from aiogram.types import InlineKeyboardMarkup

        keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)

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

        await api_client.close()

    except Exception as e:
        logger.error(f"Помилка відображення продуктів: {e}", exc_info=True)
        error_msg = localization.get_error_text("error.display_results_error", lang)
        if is_callback:
            await message.edit_text(error_msg, reply_markup=back_button_keyboard(lang=lang))
        else:
            await message.answer(error_msg, reply_markup=back_button_keyboard(lang=lang))


def _apply_local_filters(products: List[Dict], filters: Dict) -> List[Dict]:
    filtered = products

    if filters.get("product"):
        filtered = [p for p in filtered if p.get("symbol") == filters["product"].upper()]

    if filters.get("type"):
        if filters["type"] == "flexible":

            def is_flexible_product(p):

                product_type = p.get("product_type")
                if product_type and isinstance(product_type, str):
                    product_type_lower = product_type.lower()
                    if any(term in product_type_lower for term in ["flexible", "simpleflexible"]):
                        return True

                return p.get("lock_period_days", 0) == 0

            filtered = [p for p in filtered if is_flexible_product(p)]

        elif filters["type"] == "locked":

            def is_locked_product(p):

                product_type = p.get("product_type")
                if product_type and isinstance(product_type, str):
                    product_type_lower = product_type.lower()
                    if any(term in product_type_lower for term in ["locked", "fixed", "bonded"]):
                        return True

                return p.get("lock_period_days", 0) > 0

            filtered = [p for p in filtered if is_locked_product(p)]

    if filters.get("apy_min"):
        filtered = [p for p in filtered if p.get("apy", 0) >= filters["apy_min"]]
    if filters.get("apy_max"):
        filtered = [p for p in filtered if p.get("apy", 0) <= filters["apy_max"]]

    sort_by = filters.get("sort_by", "apy_desc")
    if sort_by == "popularity":
        if filters.get("popularity_fallback"):
            filtered.sort(key=lambda x: x.get("apy", 0), reverse=True)

    elif sort_by == "apy_desc":
        filtered.sort(key=lambda x: x.get("apy", 0), reverse=True)
    elif sort_by == "apy_asc":
        filtered.sort(key=lambda x: x.get("apy", 0))

    return filtered


@router.callback_query(F.data.startswith("exchange_") & F.data.contains("_prev:"))
async def prev_page_handler(callback: CallbackQuery, state: FSMContext) -> None:
    # Get language from state
    data = await state.get_data()
    lang = data.get("lang", "ua")

    try:
        data_parts = callback.data.split("_")
        provider = data_parts[1]  # exchange_binance_prev:2 -> binance
        page_str = callback.data.split(":")[1]
        current_page = int(page_str)
        new_page = current_page - 1

        await state.update_data(page=new_page)
        await callback.answer()
        await _display_exchange_products(
            callback.message, state, provider, new_page, is_callback=True, lang=lang
        )

    except Exception as e:
        logger.error(f"Помилка в prev_page_handler: {e}", exc_info=True)
        await callback.answer(localization.get_error_text("error.general", lang), show_alert=True)


@router.callback_query(F.data.startswith("exchange_") & F.data.contains("_next:"))
async def next_page_handler(callback: CallbackQuery, state: FSMContext) -> None:
    # Get language from state
    data = await state.get_data()
    lang = data.get("lang", "ua")

    try:
        data_parts = callback.data.split("_")
        provider = data_parts[1]  # exchange_binance_next:2 -> binance
        page_str = callback.data.split(":")[1]
        current_page = int(page_str)
        new_page = current_page + 1

        await state.update_data(page=new_page)
        await callback.answer()
        await _display_exchange_products(
            callback.message, state, provider, new_page, is_callback=True, lang=lang
        )

    except Exception as e:
        logger.error(f"Помилка в next_page_handler: {e}", exc_info=True)
        await callback.answer(localization.get_error_text("error.general", lang), show_alert=True)


@router.callback_query(F.data.startswith("filters:"))
async def show_exchange_filters(callback: CallbackQuery, state: FSMContext) -> None:
    # Get language from state
    data = await state.get_data()
    lang = data.get("lang", "ua")

    try:
        provider = callback.data.split(":")[1]

        display_name = _format_exchange_display_name(provider)
        await callback.answer(
            localization.get_text("loading.filters_for_exchange", lang, exchange=display_name)
        )

        from bot.keyboards.filters import create_exchange_filters_keyboard

        filters = await FilterStateManager.get_current_filters(state)

        display_name = _format_exchange_display_name(provider)
        await callback.message.answer(
            localization.get_text("search.filters_for_exchange_title", lang, exchange=display_name),
            reply_markup=create_exchange_filters_keyboard(provider, filters, lang=lang),
            parse_mode="HTML",
        )

    except Exception as e:
        logger.error(f"Помилка в show_exchange_filters: {e}", exc_info=True)
        await callback.answer(localization.get_error_text("error.general", lang), show_alert=True)


@router.message(F.text.startswith("/all_") & F.text.endswith("_products"))
async def show_all_exchange_products_command(message: Message, state: FSMContext) -> None:
    # Get language from state
    data = await state.get_data()
    lang = data.get("lang")
    if lang not in {"ua", "ru", "en"}:
        lang = await _resolve_user_language(message.from_user, state)

    try:
        text = message.text.strip()
        logger.info(f"📋 Отримано команду: {text} від користувача {message.from_user.id}")

        if not text.startswith("/all_") or not text.endswith("_products"):
            logger.warning(f"❌ Неправильний формат команди: {text}")
            return

        provider = text[5:-9].lower()

        logger.info(
            f"📋 Обробка команди /all_{provider}_products від користувача {message.from_user.id}"
        )

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
            try:
                telegram_id = (
                    message.from_user.id if hasattr(message, "from_user") else message.chat.id
                )
                try:
                    referral_url = await referral_link_generator.generate_link(
                        telegram_id=telegram_id, exchange="nexo", page="2"
                    )
                except Exception as e:
                    logger.warning(f"⚠️ Помилка генерації трекінгового посилання для nexo: {e}")

                    from bot.handlers.main_menu import _get_referral_url

                    referral_url = _get_referral_url("nexo")

                escaped_url = referral_url.replace("&", "&amp;")
                exchange_link = f'<a href="{escaped_url}">Nexo</a>'
                display_name = _format_exchange_display_name("nexo")

                await message.answer(
                    localization.get_text(
                        "messages.nexo_coming_soon",
                        lang,
                        exchange=display_name,
                        exchange_link=exchange_link,
                    ),
                    parse_mode="HTML",
                    link_preview_options=LinkPreviewOptions(is_disabled=True),
                )
            except Exception as e:
                logger.error(f"Помилка показу заглушки для Nexo: {e}", exc_info=True)

                from bot.handlers.main_menu import _get_referral_url

                referral_url = _get_referral_url("nexo")
                escaped_url = referral_url.replace("&", "&amp;")
                exchange_link = f'<a href="{escaped_url}">Nexo</a>'
                display_name = _format_exchange_display_name("nexo")
                await message.answer(
                    localization.get_text(
                        "messages.nexo_coming_soon",
                        lang,
                        exchange=display_name,
                        exchange_link=exchange_link,
                    ),
                    parse_mode="HTML",
                    link_preview_options=LinkPreviewOptions(is_disabled=True),
                )
            return
        else:
            await message.answer(
                f"{localization.get_error_text('error.unknown_exchange', lang, exchange=provider)}\n\n"
                f"{localization.get_text('messages.available_exchanges', lang)}"
            )
            return

        from bot.services.filter_state import FilterStateManager

        await FilterStateManager.reset_filters_on_page_change(state, "exchange_products")

        await state.update_data(current_page="exchange_products", provider=provider, page=1)

        display_name = _format_exchange_display_name(provider)
        async with LoadingIndicator(
            message,
            localization.get_text("loading.products_for_exchange", lang, exchange=display_name),
        ):
            await _display_exchange_products(message, state, provider, is_callback=False, lang=lang)

    except Exception as e:
        logger.error(f"Помилка в show_all_exchange_products_command: {e}", exc_info=True)
        await message.answer(localization.get_error_text("error.general", lang))
