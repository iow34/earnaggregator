from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext

from bot.keyboards.filters import (
    product_selection_keyboard,
    exchange_selection_keyboard,
    type_selection_keyboard,
    sort_options_keyboard,
    apy_range_keyboard,
)
from bot.utils.logger import logger
from bot.services.filter_state import FilterStateManager, FilterStates
from bot.localization import localization

router = Router(name="callback_handlers")


# "OTHER" is a special key for manual input
AVAILABLE_PRODUCTS = ["BTC", "ETH", "SOL", "USDT", "USDC", "BNB", "ADA", "DOT", "XRP", "OTHER"]
AVAILABLE_EXCHANGES = [
    "binance",
    "bybit",
    "okx",
    "mexc",
    "gate",
    "bitget",
    "kraken",
    "kucoin",
    "htx",
    "OTHER",
]


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


@router.callback_query(F.data.startswith("filter_product:"))
async def filter_exchange_product_handler(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    lang = data.get("lang", "ua")

    try:
        provider = callback.data.split(":", 1)[1]

        logger.info(f"🎯 Викликано filter_exchange_product_handler для {provider}")

        await state.set_state(FilterStates.selecting_product)
        await state.update_data(provider=provider)

        filters = await FilterStateManager.get_current_filters(state)
        current_product = filters.get("product")

        buttons = []
        row = []

        all_products_label = localization.get_text("menu.all_products", lang)
        all_products_text = (
            all_products_label if current_product is None else f"✓ {all_products_label}"
        )
        row.append(
            InlineKeyboardButton(
                text=all_products_text, callback_data=f"select_product:ВСІ_ПРОДУКТИ_{provider}"
            )
        )

        for i, product in enumerate(AVAILABLE_PRODUCTS):
            # Localize "OTHER"
            display_product = product
            if product == "OTHER":
                display_product = localization.get_text("menu.other_product", lang)
            elif product == "Інший продукт":  # Legacy fallback
                display_product = localization.get_text("menu.other_product", lang)
                product = "OTHER"

            text = f"✓ {display_product}" if product == current_product else display_product

            row.append(InlineKeyboardButton(text=text, callback_data=f"select_product:{product}"))

            if (i + 1) % 3 == 0:
                buttons.append(row)
                row = []

        if row:
            buttons.append(row)

        display_name = _format_exchange_display_name(provider)
        buttons.append(
            [
                InlineKeyboardButton(
                    text=localization.get_text("nav.back_to_exchange", lang, exchange=display_name),
                    callback_data=f"back_to_exchange:{provider}",
                )
            ]
        )

        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

        display_name = _format_exchange_display_name(provider)
        await callback.message.edit_text(
            localization.get_text(
                "menu.select_product_for_exchange_title", lang, exchange=display_name
            )
            + "\n\n"
            + localization.get_text("menu.select_product_prompt", lang),
            reply_markup=keyboard,
            parse_mode="HTML",
        )
        await callback.answer()

    except Exception as e:
        logger.error(f"Помилка в filter_exchange_product_handler: {e}", exc_info=True)
        await callback.answer(localization.get_error_text("error.general", lang), show_alert=True)


@router.callback_query(F.data == "filter_product")
async def filter_product_handler(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    lang = data.get("lang", "ua")

    try:
        await state.set_state(FilterStates.selecting_product)

        filters = await FilterStateManager.get_current_filters(state)
        current_product = filters.get("product")

        # Prepare localized product list for keyboard
        localized_products = []
        for p in AVAILABLE_PRODUCTS:
            if p == "OTHER":
                localized_products.append(localization.get_text("menu.other_product", lang))
            elif p == "Інший продукт":
                localized_products.append(localization.get_text("menu.other_product", lang))
            else:
                localized_products.append(p)

        # Note: product_selection_keyboard receives localized names, so we need to handle mapping back?
        # Actually product_selection_keyboard uses the list for text AND callback_data.

        # This complicates `select_product_handler`.
        # BETTER: Update `product_selection_keyboard` in `filters.py` to handle this mapping or pass tuples (code, label).
        # But I already updated `filters.py` to take `products: List[str]`.
        # I should rely on `AVAILABLE_PRODUCTS` codes being consistent and handle localization inside `product_selection_keyboard`?
        # No, `product_selection_keyboard` iterates list.

        # Let's construct custom keyboard here or pass codes and let `filters.py` localize?
        # I passed `lang` to `product_selection_keyboard` in `filters.py`.
        # But `filters.py` iterates `products` and uses `text=product`.
        # So if I pass ["BTC", "OTHER"], it shows "OTHER".
        # I need `filters.py` to check for "OTHER" and localize it.
        # I didn't add that check in `filters.py` update. I missed it.

        # Workaround: Build keyboard manually here or pass localized strings and map in handler.
        # Or simpler: Pass `lang` to `product_selection_keyboard` (I did) and let IT handle "OTHER".
        # I need to re-update `filters.py` to handle "OTHER" -> localized text.
        # OR I pass a list of objects/tuples.

        # Let's stick to modifying `filters.py` later or doing it locally here.
        # For now, I will generate the keyboard manually here to ensure correctness.

        buttons = []
        row = []
        for i, product in enumerate(AVAILABLE_PRODUCTS):
            display_text = product
            if product == "OTHER" or product == "Інший продукт":
                display_text = localization.get_text("menu.other_product", lang)
                # Use "OTHER" code in callback
                code = "OTHER"
            else:
                code = product

            text = f"✓ {display_text}" if code == current_product else display_text

            row.append(InlineKeyboardButton(text=text, callback_data=f"select_product:{code}"))

            if (i + 1) % 3 == 0:
                buttons.append(row)
                row = []

        if row:
            buttons.append(row)

        buttons.append(
            [
                InlineKeyboardButton(
                    text=localization.get_text("nav.back", lang), callback_data="back_to_filters"
                )
            ]
        )

        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

        await callback.message.edit_text(
            localization.get_text("menu.select_product_title", lang),
            reply_markup=keyboard,
            parse_mode="HTML",
        )
        await callback.answer()

    except Exception as e:
        logger.error(f"Помилка в filter_product_handler: {e}", exc_info=True)
        await callback.answer(localization.get_error_text("error.general", lang), show_alert=True)


@router.callback_query(F.data.startswith("select_product:"))
async def select_product_handler(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    lang = data.get("lang", "ua")

    try:
        product = callback.data.split(":", 1)[1]

        logger.info(f"🎯 Викликано select_product_handler з продуктом: {product}")

        if product.startswith("ВСІ_ПРОДУКТИ_"):
            provider = product.split("_")[-1]
            logger.info(f"🎯 Скидаємо фільтр продукту для {provider}")
            await FilterStateManager.apply_filter(state, "product", None)
            await callback.answer(localization.get_text("messages.all_products_shown", lang))

        elif product == "OTHER" or product == "Інший продукт":
            await state.set_state(FilterStates.entering_product_manual)
            await callback.answer(localization.get_text("messages.enter_product", lang))

            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text=localization.get_text("nav.cancel", lang),
                            callback_data="cancel_manual_product_input",
                        )
                    ]
                ]
            )

            await callback.message.edit_text(
                localization.get_text("menu.manual_product_input_title", lang)
                + "\n\n"
                + localization.get_text("menu.manual_product_input_prompt", lang)
                + "\n\n"
                + localization.get_text("menu.manual_product_input_hint", lang),
                reply_markup=keyboard,
                parse_mode="HTML",
            )
            return
        else:
            await FilterStateManager.apply_filter(state, "product", product)
            await callback.answer(
                localization.get_text("messages.product_selected", lang, product=product)
            )

            data = await state.get_data()
            current_page = data.get("current_page")

            if current_page == "flexible_products":
                from bot.handlers.filtered_products import _display_flexible_products

                await _display_flexible_products(
                    callback.message, state, page=1, is_callback=True, lang=lang
                )
            elif current_page == "locked_products":
                from bot.handlers.filtered_products import _display_locked_products

                await _display_locked_products(
                    callback.message, state, page=1, is_callback=True, lang=lang
                )
            elif current_page == "all_products":
                from bot.handlers.filtered_products import _display_all_products

                await _display_all_products(
                    callback.message, state, page=1, is_callback=True, lang=lang
                )
            elif current_page == "exchange_products":
                provider = data.get("provider")
                if provider:
                    from bot.handlers.exchange_products import _display_exchange_products

                    await _display_exchange_products(
                        callback.message, state, provider, page=1, is_callback=True, lang=lang
                    )
                else:
                    from bot.handlers.filtered_products import show_product_all_exchanges

                    await show_product_all_exchanges(callback.message, state, product, lang=lang)
            else:
                from bot.handlers.filtered_products import show_product_all_exchanges

                await show_product_all_exchanges(callback.message, state, product, lang=lang)

    except Exception as e:
        logger.error(f"Помилка в select_product_handler: {e}", exc_info=True)
        await callback.answer(localization.get_error_text("error.general", lang), show_alert=True)


@router.callback_query(F.data == "filter_exchange")
async def filter_exchange_handler(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    lang = data.get("lang", "ua")

    try:
        await state.set_state(FilterStates.selecting_exchange)

        filters = await FilterStateManager.get_current_filters(state)
        current_exchange = filters.get("exchange")

        provider = data.get("provider")

        # Manually build keyboard to handle localization of "OTHER"
        buttons = []
        for exchange in AVAILABLE_EXCHANGES:
            display_text = _format_exchange_display_name(exchange)
            code = exchange
            if exchange == "OTHER" or exchange == "Інші біржі":
                display_text = localization.get_text("menu.other_exchange", lang)
                code = "OTHER"

            text = f"✓ {display_text}" if code == current_exchange else display_text
            buttons.append(
                [InlineKeyboardButton(text=text, callback_data=f"select_exchange:{code}")]
            )

        buttons.append(
            [
                InlineKeyboardButton(
                    text=localization.get_text("nav.all_exchanges", lang),
                    callback_data="select_exchange:all",
                )
            ]
        )

        if provider:
            buttons.append(
                [
                    InlineKeyboardButton(
                        text=localization.get_text("nav.back", lang),
                        callback_data=f"back_to_exchange:{provider}",
                    )
                ]
            )
        else:
            buttons.append(
                [
                    InlineKeyboardButton(
                        text=localization.get_text("nav.back", lang),
                        callback_data="back_to_filters",
                    )
                ]
            )

        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

        await callback.message.edit_text(
            localization.get_text("menu.select_exchange_title", lang),
            reply_markup=keyboard,
            parse_mode="HTML",
        )
        await callback.answer()

    except Exception as e:
        logger.error(f"Помилка в filter_exchange_handler: {e}", exc_info=True)
        await callback.answer(localization.get_error_text("error.general", lang), show_alert=True)


@router.callback_query(F.data.startswith("select_exchange:"))
async def select_exchange_handler(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    lang = data.get("lang", "ua")

    try:
        exchange = callback.data.split(":", 1)[1]

        if exchange == "all":
            await FilterStateManager.apply_filter(state, "exchange", None)
            await callback.answer(localization.get_text("messages.all_exchanges_shown", lang))
        elif exchange == "OTHER" or exchange == "Інші біржі":
            await state.set_state(FilterStates.entering_exchange_manual)
            await callback.answer(localization.get_text("messages.enter_exchange", lang))

            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text=localization.get_text("nav.cancel", lang),
                            callback_data="cancel_manual_exchange_input",
                        )
                    ]
                ]
            )

            await callback.message.edit_text(
                localization.get_text("menu.manual_exchange_input_title", lang)
                + "\n\n"
                + localization.get_text("menu.manual_exchange_input_prompt", lang)
                + "\n\n"
                + localization.get_text("menu.manual_exchange_input_hint", lang),
                reply_markup=keyboard,
                parse_mode="HTML",
            )
            return
        else:
            await FilterStateManager.apply_filter(state, "exchange", exchange)
            display_name = _format_exchange_display_name(exchange)
            await callback.answer(
                localization.get_text("messages.exchange_selected", lang, exchange=display_name)
            )

        data = await state.get_data()
        current_page = data.get("current_page")

        if current_page == "flexible_products":
            from bot.handlers.filtered_products import _display_flexible_products

            await _display_flexible_products(
                callback.message, state, page=1, is_callback=True, lang=lang
            )
        elif current_page == "locked_products":
            from bot.handlers.filtered_products import _display_locked_products

            await _display_locked_products(
                callback.message, state, page=1, is_callback=True, lang=lang
            )
        elif current_page == "all_products":
            from bot.handlers.filtered_products import _display_all_products

            await _display_all_products(
                callback.message, state, page=1, is_callback=True, lang=lang
            )
        else:
            await callback.message.edit_text(
                localization.get_text("messages.applying_filter", lang), parse_mode="HTML"
            )

    except Exception as e:
        logger.error(f"Помилка в select_exchange_handler: {e}", exc_info=True)
        await callback.answer(localization.get_error_text("error.general", lang), show_alert=True)


@router.callback_query(F.data == "filter_type" or F.data.startswith("filter_type:"))
async def filter_type_handler(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    lang = data.get("lang", "ua")

    try:
        await state.set_state(FilterStates.selecting_type)

        filters = await FilterStateManager.get_current_filters(state)
        current_type = filters.get("type")

        provider = None
        if ":" in callback.data:
            provider = callback.data.split(":", 1)[1]

            await state.update_data(provider=provider)

        await callback.message.edit_text(
            localization.get_text("menu.select_type_title", lang),
            reply_markup=type_selection_keyboard(current_type, provider=provider, lang=lang),
            parse_mode="HTML",
        )
        await callback.answer()

    except Exception as e:
        logger.error(f"Помилка в filter_type_handler: {e}", exc_info=True)
        await callback.answer(localization.get_error_text("error.general", lang), show_alert=True)


@router.callback_query(F.data.startswith("select_type:"))
async def select_type_handler(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    lang = data.get("lang", "ua")

    try:
        parts = callback.data.split(":")
        type_value = parts[1]
        provider_from_callback = parts[2] if len(parts) > 2 else None

        if type_value == "all":
            await FilterStateManager.apply_filter(state, "type", None)
            await callback.answer(localization.get_text("messages.all_types_shown", lang))
        else:
            await FilterStateManager.apply_filter(state, "type", type_value)
            await callback.answer(
                localization.get_text("messages.type_selected", lang, type=type_value.title())
            )

        data = await state.get_data()
        current_page = data.get("current_page")

        provider = provider_from_callback or data.get("provider")

        if current_page == "exchange_products" or provider_from_callback:
            provider = provider or "binance"
            from bot.handlers.exchange_products import _display_exchange_products

            await _display_exchange_products(
                callback.message, state, provider, page=1, is_callback=True, lang=lang
            )
        elif current_page == "all_products":
            from bot.handlers.filtered_products import _display_all_products

            await _display_all_products(
                callback.message, state, page=1, is_callback=True, lang=lang
            )
        elif current_page == "flexible_products":
            from bot.handlers.filtered_products import _display_flexible_products

            await _display_flexible_products(
                callback.message, state, page=1, is_callback=True, lang=lang
            )
        elif current_page == "locked_products":
            from bot.handlers.filtered_products import _display_locked_products

            await _display_locked_products(
                callback.message, state, page=1, is_callback=True, lang=lang
            )
        else:
            from bot.handlers.main_menu import show_main_page

            await show_main_page(callback.message, state, lang=lang)

    except Exception as e:
        logger.error(f"Помилка в select_type_handler: {e}", exc_info=True)
        await callback.answer(localization.get_error_text("error.general", lang), show_alert=True)


@router.callback_query(
    F.data.startswith("sort:")
    & ~F.data.startswith("sort:apy")
    & ~F.data.startswith("sort:popularity")
)
async def sort_exchange_handler(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    lang = data.get("lang", "ua")

    try:
        provider = callback.data.split(":", 1)[1]
        await state.update_data(provider=provider)

        filters = await FilterStateManager.get_current_filters(state)
        current_sort = filters.get("sort_by", "popularity")

        display_name = _format_exchange_display_name(provider)
        await callback.message.edit_text(
            localization.get_text("menu.select_sort_for_exchange", lang, exchange=display_name),
            reply_markup=sort_options_keyboard(current_sort, provider=provider, lang=lang),
            parse_mode="HTML",
        )
        await callback.answer()

    except Exception as e:
        logger.error(f"Помилка в sort_exchange_handler: {e}", exc_info=True)
        await callback.answer(localization.get_error_text("error.general", lang), show_alert=True)


@router.callback_query(F.data == "sort_options")
async def sort_options_handler(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    lang = data.get("lang", "ua")

    try:
        filters = await FilterStateManager.get_current_filters(state)
        current_sort = filters.get("sort_by", "popularity")

        provider = data.get("provider", "binance")

        await callback.message.edit_text(
            localization.get_text("menu.select_sort_title", lang),
            reply_markup=sort_options_keyboard(current_sort, provider=provider, lang=lang),
            parse_mode="HTML",
        )
        await callback.answer()

    except Exception as e:
        logger.error(f"Помилка в sort_options_handler: {e}", exc_info=True)
        await callback.answer(localization.get_error_text("error.general", lang), show_alert=True)


@router.callback_query(F.data.startswith("sort_options:"))
async def exchange_sort_options_handler(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    lang = data.get("lang", "ua")

    try:
        provider = callback.data.split(":", 1)[1]

        filters = await FilterStateManager.get_current_filters(state)
        current_sort = filters.get("sort_by", "popularity")

        display_name = _format_exchange_display_name(provider)
        await callback.message.edit_text(
            localization.get_text("menu.select_sort_for_exchange", lang, exchange=display_name),
            reply_markup=sort_options_keyboard(current_sort, provider=provider, lang=lang),
            parse_mode="HTML",
        )
        await callback.answer()

    except Exception as e:
        logger.error(f"Помилка в exchange_sort_options_handler: {e}", exc_info=True)
        await callback.answer(localization.get_error_text("error.general", lang), show_alert=True)


@router.callback_query(F.data.startswith("sort:"))
async def apply_sort_handler(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    lang = data.get("lang", "ua")

    try:
        sort_type = callback.data.split(":", 1)[1]

        if sort_type.endswith("_disabled"):
            await callback.answer(
                localization.get_text("messages.feature_in_dev", lang), show_alert=True
            )
            return

        await state.update_data(sort_by=sort_type, page=1)

        sort_label = localization.get_text(f"menu.sort_{sort_type}", lang)
        # fallback if key missing
        if "menu.sort_" in sort_label:
            sort_label = sort_type

        await callback.answer(localization.get_text("messages.sort_applied", lang, sort=sort_label))

        data = await state.get_data()
        provider = data.get("provider")
        current_page = data.get("current_page")

        if current_page == "flexible_products":
            from bot.handlers.filtered_products import _display_flexible_products

            await _display_flexible_products(
                callback.message, state, page=1, is_callback=True, lang=lang
            )
        elif current_page == "locked_products":
            from bot.handlers.filtered_products import _display_locked_products

            await _display_locked_products(
                callback.message, state, page=1, is_callback=True, lang=lang
            )
        elif current_page == "all_products":
            from bot.handlers.filtered_products import _display_all_products

            await _display_all_products(
                callback.message, state, page=1, is_callback=True, lang=lang
            )
        elif provider:
            from bot.handlers.exchange_products import _display_exchange_products

            await _display_exchange_products(
                callback.message, state, provider, page=1, is_callback=True, lang=lang
            )
        else:
            logger.warning(f"⚠️ Provider не знайдено в state для сортування {sort_type}")
            await callback.message.edit_text(
                localization.get_text("messages.sort_applied_select_exchange", lang),
                parse_mode="HTML",
            )

    except Exception as e:
        logger.error(f"Помилка в apply_sort_handler: {e}", exc_info=True)
        await callback.answer(localization.get_error_text("error.general", lang), show_alert=True)


@router.callback_query(F.data == "reset_filters" or F.data.startswith("reset_filters:"))
async def reset_filters_handler(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    lang = data.get("lang", "ua")

    try:
        provider_from_callback = None
        if ":" in callback.data:
            provider_from_callback = callback.data.split(":", 1)[1]

        provider = provider_from_callback or data.get("provider")
        keep_exchange = provider is not None
        current_page = data.get("current_page")

        keep_type = None
        if current_page == "flexible_products":
            keep_type = "flexible"
        elif current_page == "locked_products":
            keep_type = "locked"
        elif current_page == "all_products":
            keep_type = "all"

        await FilterStateManager.reset_filters(state, keep_exchange=keep_exchange)

        if keep_type:
            await FilterStateManager.apply_filter(state, "type", keep_type, reset_page=False)

        await callback.answer(localization.get_text("messages.filters_reset", lang))

        if current_page == "exchange_products" or provider_from_callback:
            provider = provider or "binance"
            from bot.handlers.exchange_products import _display_exchange_products

            await _display_exchange_products(
                callback.message, state, provider, page=1, is_callback=True, lang=lang
            )
        elif current_page == "flexible_products":
            from bot.handlers.filtered_products import _display_flexible_products

            await _display_flexible_products(
                callback.message, state, page=1, is_callback=True, lang=lang
            )
        elif current_page == "locked_products":
            from bot.handlers.filtered_products import _display_locked_products

            await _display_locked_products(
                callback.message, state, page=1, is_callback=True, lang=lang
            )
        elif current_page == "all_products":
            from bot.handlers.filtered_products import _display_all_products

            await _display_all_products(
                callback.message, state, page=1, is_callback=True, lang=lang
            )
        else:
            from bot.handlers.main_menu import show_main_page

            await show_main_page(callback.message, state, lang=lang)

    except Exception as e:
        logger.error(f"Помилка в reset_filters_handler: {e}", exc_info=True)
        await callback.answer(localization.get_error_text("error.general", lang), show_alert=True)


@router.callback_query(F.data.startswith("back_to_exchange:"))
async def back_to_exchange_handler(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    lang = data.get("lang", "ua")

    try:
        await callback.answer()

        provider = callback.data.split(":", 1)[1].lower()

        if provider:
            await state.update_data(provider=provider)

            from bot.handlers.exchange_products import _display_exchange_products

            await _display_exchange_products(
                callback.message, state, provider, page=1, is_callback=True, lang=lang
            )
        else:
            from bot.handlers.main_menu import show_main_page

            await show_main_page(callback.message, state, lang=lang)

    except Exception as e:
        logger.error(f"Помилка в back_to_exchange_handler: {e}", exc_info=True)
        await callback.answer(localization.get_error_text("error.general", lang), show_alert=True)


@router.callback_query(F.data == "back_from_sort")
async def back_from_sort_handler(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    lang = data.get("lang", "ua")

    try:
        await callback.answer()

        current_page = data.get("current_page")

        if current_page == "flexible_products":
            from bot.handlers.filtered_products import _display_flexible_products

            await _display_flexible_products(
                callback.message, state, page=1, is_callback=True, lang=lang
            )
        elif current_page == "locked_products":
            from bot.handlers.filtered_products import _display_locked_products

            await _display_locked_products(
                callback.message, state, page=1, is_callback=True, lang=lang
            )
        elif current_page == "all_products":
            from bot.handlers.filtered_products import _display_all_products

            await _display_all_products(
                callback.message, state, page=1, is_callback=True, lang=lang
            )
        elif current_page == "exchange_products":
            provider = data.get("provider", "binance")
            from bot.handlers.exchange_products import _display_exchange_products

            await _display_exchange_products(
                callback.message, state, provider, page=1, is_callback=True, lang=lang
            )
        else:
            from bot.handlers.main_menu import show_main_page

            await show_main_page(callback.message, state, lang=lang)

    except Exception as e:
        logger.error(f"Помилка в back_from_sort_handler: {e}", exc_info=True)
        await callback.answer(localization.get_error_text("error.general", lang), show_alert=True)


@router.callback_query(F.data == "back_to_filters")
async def back_to_filters_handler(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    lang = data.get("lang", "ua")

    try:
        await callback.answer()

        current_page = data.get("current_page")

        if current_page == "exchange_products":
            provider = data.get("provider", "binance")
            from bot.handlers.exchange_products import _display_exchange_products

            await _display_exchange_products(
                callback.message, state, provider, page=1, is_callback=True, lang=lang
            )
        elif current_page == "all_products":
            from bot.handlers.filtered_products import _display_all_products

            await _display_all_products(
                callback.message, state, page=1, is_callback=True, lang=lang
            )
        elif current_page == "flexible_products":
            from bot.handlers.filtered_products import _display_flexible_products

            await _display_flexible_products(
                callback.message, state, page=1, is_callback=True, lang=lang
            )
        elif current_page == "locked_products":
            from bot.handlers.filtered_products import _display_locked_products

            await _display_locked_products(
                callback.message, state, page=1, is_callback=True, lang=lang
            )
        else:
            from bot.handlers.main_menu import show_main_page

            await show_main_page(callback.message, state, lang=lang)

    except Exception as e:
        logger.error(f"Помилка в back_to_filters_handler: {e}", exc_info=True)
        await callback.answer(localization.get_error_text("error.general", lang), show_alert=True)


@router.callback_query(F.data == "noop")
async def noop_handler(callback: CallbackQuery) -> None:
    await callback.answer()


@router.message(FilterStates.entering_exchange_manual, F.text)
async def process_filter_manual_exchange_input(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    lang = data.get("lang", "ua")

    try:
        exchange_input = message.text.strip().lower()

        if not exchange_input:
            await message.answer(localization.get_error_text("error.invalid_input", lang))
            return

        import re

        if not re.match(r"^[a-z0-9-]+$", exchange_input):
            await message.answer(
                localization.get_error_text("error.invalid_input_chars", lang)
            )  # key might be missing, need to ensure it exists or use generic
            return

        if len(exchange_input) > 20:
            await message.answer(localization.get_error_text("error.input_too_long", lang))
            return

        await FilterStateManager.apply_filter(state, "exchange", exchange_input)
        await state.set_state(None)

        await message.answer(
            localization.get_text("messages.exchange_selected", lang, exchange=exchange_input)
        )

        data = await state.get_data()
        current_page = data.get("current_page")

        if current_page == "flexible_products":
            from bot.handlers.filtered_products import _display_flexible_products

            await _display_flexible_products(message, state, page=1, is_callback=False, lang=lang)
        elif current_page == "locked_products":
            from bot.handlers.filtered_products import _display_locked_products

            await _display_locked_products(message, state, page=1, is_callback=False, lang=lang)
        elif current_page == "all_products":
            from bot.handlers.filtered_products import _display_all_products

            await _display_all_products(message, state, page=1, is_callback=False, lang=lang)
        else:
            from bot.handlers.filtered_products import show_product_all_exchanges

            await show_product_all_exchanges(
                message, state, data.get("product_filter"), lang=lang
            )  # Assuming product_filter is stored in data or derived

    except Exception as e:
        logger.error(f"Помилка в process_filter_manual_exchange_input: {e}", exc_info=True)
        await message.answer(localization.get_error_text("error.general", lang))


@router.callback_query(F.data == "cancel_manual_exchange_input")
async def cancel_filter_manual_exchange_input(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    lang = data.get("lang", "ua")

    try:
        await state.set_state(None)
        await callback.answer(localization.get_text("messages.cancelled", lang))

        current_page = data.get("current_page")

        if current_page == "flexible_products":
            from bot.handlers.filtered_products import _display_flexible_products

            await _display_flexible_products(
                callback.message, state, page=1, is_callback=True, lang=lang
            )
        elif current_page == "locked_products":
            from bot.handlers.filtered_products import _display_locked_products

            await _display_locked_products(
                callback.message, state, page=1, is_callback=True, lang=lang
            )
        elif current_page == "all_products":
            from bot.handlers.filtered_products import _display_all_products

            await _display_all_products(
                callback.message, state, page=1, is_callback=True, lang=lang
            )
        else:
            from bot.handlers.main_menu import show_main_page

            await show_main_page(callback.message, state, lang=lang)

    except Exception as e:
        logger.error(f"Помилка в cancel_filter_manual_exchange_input: {e}", exc_info=True)
        await callback.answer(localization.get_error_text("error.general", lang), show_alert=True)


@router.message(FilterStates.entering_product_manual, F.text)
async def process_filter_manual_product_input(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    lang = data.get("lang", "ua")

    try:
        product_input = message.text.strip().upper()

        if not product_input:
            await message.answer(localization.get_error_text("error.product_input_empty", lang))
            return

        import re

        if not re.match(r"^[A-Z0-9-]+$", product_input):
            await message.answer(
                localization.get_error_text("error.product_input_invalid_chars", lang)
            )
            return

        if len(product_input) > 20:
            await message.answer(localization.get_error_text("error.product_input_too_long", lang))
            return

        await FilterStateManager.apply_filter(state, "product", product_input)
        await state.set_state(None)

        await message.answer(
            localization.get_text("messages.product_selected", lang, product=product_input)
        )

        current_page = data.get("current_page")

        if current_page == "flexible_products":
            from bot.handlers.filtered_products import _display_flexible_products

            await _display_flexible_products(message, state, page=1, is_callback=False, lang=lang)
        elif current_page == "locked_products":
            from bot.handlers.filtered_products import _display_locked_products

            await _display_locked_products(message, state, page=1, is_callback=False, lang=lang)
        elif current_page == "all_products":
            from bot.handlers.filtered_products import _display_all_products

            await _display_all_products(message, state, page=1, is_callback=False, lang=lang)
        elif current_page == "exchange_products":
            provider = data.get("provider")
            if provider:
                from bot.handlers.exchange_products import _display_exchange_products

                await _display_exchange_products(
                    message, state, provider, page=1, is_callback=False, lang=lang
                )
            else:
                from bot.handlers.filtered_products import show_product_all_exchanges

                await show_product_all_exchanges(message, state, product_input, lang=lang)
        else:
            from bot.handlers.filtered_products import show_product_all_exchanges

            await show_product_all_exchanges(message, state, product_input, lang=lang)

    except Exception as e:
        logger.error(f"Помилка в process_filter_manual_product_input: {e}", exc_info=True)
        await message.answer(localization.get_error_text("error.general", lang))


@router.callback_query(F.data == "cancel_manual_product_input")
async def cancel_filter_manual_product_input(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    lang = data.get("lang", "ua")

    try:
        await state.set_state(None)
        await callback.answer(localization.get_text("messages.cancelled", lang))

        current_page = data.get("current_page")
        current_page_num = data.get("page", 1)

        if current_page == "flexible_products":
            from bot.handlers.filtered_products import _display_flexible_products

            await _display_flexible_products(
                callback.message, state, page=current_page_num, is_callback=True, lang=lang
            )
        elif current_page == "locked_products":
            from bot.handlers.filtered_products import _display_locked_products

            await _display_locked_products(
                callback.message, state, page=current_page_num, is_callback=True, lang=lang
            )
        elif current_page == "all_products":
            from bot.handlers.filtered_products import _display_all_products

            await _display_all_products(
                callback.message, state, page=current_page_num, is_callback=True, lang=lang
            )
        elif current_page == "exchange_products":
            provider = data.get("provider")
            if provider:
                from bot.handlers.exchange_products import _display_exchange_products

                await _display_exchange_products(
                    callback.message,
                    state,
                    provider,
                    page=current_page_num,
                    is_callback=True,
                    lang=lang,
                )
            else:
                from bot.handlers.main_menu import show_main_page

                await show_main_page(callback.message, state, lang=lang)
        else:
            from bot.handlers.main_menu import show_main_page

            await show_main_page(callback.message, state, lang=lang)

    except Exception as e:
        logger.error(f"Помилка в cancel_filter_manual_product_input: {e}", exc_info=True)
        await callback.answer(localization.get_error_text("error.general", lang), show_alert=True)
