from typing import Optional, List, Dict
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from bot.localization import localization


def filter_keyboard(
    current_filters: dict, show_reset: bool = True, show_sort: bool = True, lang: str = "ua"
) -> InlineKeyboardMarkup:
    buttons = []

    row1 = []

    product_text = (
        f"🪙 {current_filters.get('product', localization.get_text('menu.product', lang))} ▼"
    )
    row1.append(InlineKeyboardButton(text=product_text, callback_data="filter_product"))

    exchange_val = current_filters.get("exchange")
    exchange_label = localization.get_text("menu.exchange", lang)
    exchange_text = f"🏦 {exchange_val.title() if exchange_val else exchange_label} ▼"
    row1.append(InlineKeyboardButton(text=exchange_text, callback_data="filter_exchange"))

    buttons.append(row1)

    row2 = []

    type_val = current_filters.get("type")
    type_label = localization.get_text("menu.type", lang)
    type_text = f"⚡ {type_val.title() if type_val else type_label} ▼"
    row2.append(InlineKeyboardButton(text=type_text, callback_data="filter_type"))

    apy_text = f"📊 {localization.get_text('menu.apy', lang)} ▼"
    if current_filters.get("apy_min") or current_filters.get("apy_max"):
        apy_text = f"📊 {localization.get_text('menu.apy', lang)} ✓"
    row2.append(InlineKeyboardButton(text=apy_text, callback_data="filter_apy"))

    buttons.append(row2)

    row3 = []

    if show_sort:
        sort_by = current_filters.get("sort_by", "popularity")
        sort_text = f"📊 {localization.get_text('menu.sort', lang)}"
        if sort_by == "apy_desc":
            sort_text = "📈 APY ↓"
        elif sort_by == "apy_asc":
            sort_text = "📉 APY ↑"

        row3.append(InlineKeyboardButton(text=sort_text, callback_data="sort_options"))

    if show_reset:
        row3.append(
            InlineKeyboardButton(
                text=f"♻️ {localization.get_text('menu.reset', lang)}", callback_data="reset_filters"
            )
        )

    if row3:
        buttons.append(row3)

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def product_selection_keyboard(
    products: List[str], current_product: Optional[str] = None, columns: int = 3, lang: str = "ua"
) -> InlineKeyboardMarkup:
    buttons = []
    row = []

    for i, product in enumerate(products):
        text = f"✓ {product}" if product == current_product else product

        row.append(InlineKeyboardButton(text=text, callback_data=f"select_product:{product}"))

        if (i + 1) % columns == 0:
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

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def exchange_selection_keyboard(
    exchanges: List[str],
    current_exchange: Optional[str] = None,
    provider: Optional[str] = None,
    lang: str = "ua",
) -> InlineKeyboardMarkup:
    buttons = []

    for exchange in exchanges:
        text = f"✓ {exchange.title()}" if exchange == current_exchange else exchange.title()
        buttons.append(
            [InlineKeyboardButton(text=text, callback_data=f"select_exchange:{exchange}")]
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
                    text=localization.get_text("nav.back", lang), callback_data="back_to_filters"
                )
            ]
        )

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def type_selection_keyboard(
    current_type: Optional[str] = None, provider: Optional[str] = None, lang: str = "ua"
) -> InlineKeyboardMarkup:
    types = [
        ("flexible", localization.get_text("table.product.flexible", lang)),
        ("locked", localization.get_text("table.product.locked", lang)),
        ("all", localization.get_text("nav.all_types", lang)),
    ]

    buttons = []
    for type_value, type_label in types:
        text = f"✓ {type_label}" if type_value == current_type else type_label

        callback_data = (
            f"select_type:{type_value}:{provider}" if provider else f"select_type:{type_value}"
        )

        buttons.append([InlineKeyboardButton(text=text, callback_data=callback_data)])

    if provider:
        back_callback = f"back_to_exchange:{provider}"
    else:
        back_callback = "back_to_filters"

    buttons.append(
        [
            InlineKeyboardButton(
                text=localization.get_text("nav.back", lang), callback_data=back_callback
            )
        ]
    )

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def sort_options_keyboard(
    current_sort: str = "popularity", provider: str = "binance", lang: str = "ua"
) -> InlineKeyboardMarkup:
    options = [
        ("apy_desc", localization.get_text("menu.sort_apy_desc", lang)),
        ("apy_asc", localization.get_text("menu.sort_apy_asc", lang)),
        ("popularity", localization.get_text("menu.sort_popularity", lang)),
    ]

    buttons = []
    for sort_value, sort_label in options:
        text = f"✓ {sort_label}" if sort_value == current_sort else sort_label

        buttons.append([InlineKeyboardButton(text=text, callback_data=f"sort:{sort_value}")])

    buttons.append(
        [
            InlineKeyboardButton(
                text=localization.get_text("nav.back", lang), callback_data="back_from_sort"
            )
        ]
    )

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def apy_range_keyboard(lang: str = "ua") -> InlineKeyboardMarkup:
    ranges = [
        ("0-5", "📊 0-5%"),
        ("5-10", "📈 5-10%"),
        ("10-20", "🔥 10-20%"),
        ("20+", "💥 20%+"),
        ("custom", f"✏️ {localization.get_text('menu.custom_range', lang)}"),
    ]

    buttons = []
    for range_value, range_label in ranges:
        buttons.append(
            [InlineKeyboardButton(text=range_label, callback_data=f"select_apy:{range_value}")]
        )

    buttons.append(
        [
            InlineKeyboardButton(
                text=localization.get_text("nav.back", lang), callback_data="back_to_filters"
            )
        ]
    )

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def create_exchange_filters_keyboard(
    provider: str, current_filters: dict = None, lang: str = "ua"
) -> InlineKeyboardMarkup:
    if current_filters is None:
        current_filters = {}

    sort_by = current_filters.get("sort_by", "popularity")
    sort_text = f"📊 {localization.get_text('menu.sort', lang)}"
    if sort_by == "apy_desc":
        sort_text = "📈 APY ↓"
    elif sort_by == "apy_asc":
        sort_text = "📉 APY ↑"

    buttons = [[InlineKeyboardButton(text=sort_text, callback_data=f"sort_options:{provider}")]]

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def flexible_products_keyboard(
    filters: Dict,
    page: int = 1,
    total_pages: int = 1,
    show_pagination: bool = True,
    lang: str = "ua",
) -> InlineKeyboardMarkup:
    buttons = []

    row1 = []

    sort_by = filters.get("sort_by", "popularity")
    sort_text = f"📊 {localization.get_text('menu.sort', lang)}"
    if sort_by == "apy_desc":
        sort_text = "📈 APY ↓"
    elif sort_by == "apy_asc":
        sort_text = "📉 APY ↑"
    row1.append(InlineKeyboardButton(text=sort_text, callback_data="sort_options"))

    product = filters.get("product")
    product_text = (
        f"🪙 {product}" if product else f"🪙 {localization.get_text('menu.product', lang)}"
    )
    row1.append(InlineKeyboardButton(text=product_text, callback_data="filter_product"))

    exchange = filters.get("exchange")
    exchange_text = (
        f"🏦 {exchange.title()}"
        if exchange
        else f"🏦 {localization.get_text('menu.exchange', lang)}"
    )
    row1.append(InlineKeyboardButton(text=exchange_text, callback_data="filter_exchange"))

    buttons.append(row1)

    buttons.append(
        [
            InlineKeyboardButton(
                text=f"♻️ {localization.get_text('menu.reset_filters', lang)}",
                callback_data="reset_filters",
            )
        ]
    )

    if show_pagination and total_pages > 1:
        nav_row = []
        if page > 1:
            nav_row.append(
                InlineKeyboardButton(
                    text=localization.get_text("nav.prev", lang),
                    callback_data=f"flexible_prev:{page}",
                )
            )

        nav_row.append(InlineKeyboardButton(text=f"{page}/{total_pages}", callback_data="noop"))

        if page < total_pages:
            nav_row.append(
                InlineKeyboardButton(
                    text=localization.get_text("nav.next", lang),
                    callback_data=f"flexible_next:{page}",
                )
            )

        buttons.append(nav_row)

    buttons.append(
        [
            InlineKeyboardButton(
                text=localization.get_text("nav.to_main", lang), callback_data="back_to_main"
            )
        ]
    )

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def locked_products_keyboard(
    filters: Dict,
    page: int = 1,
    total_pages: int = 1,
    show_pagination: bool = True,
    lang: str = "ua",
) -> InlineKeyboardMarkup:
    buttons = []

    row1 = []

    sort_by = filters.get("sort_by", "popularity")
    sort_text = f"📊 {localization.get_text('menu.sort', lang)}"
    if sort_by == "apy_desc":
        sort_text = "📈 APY ↓"
    elif sort_by == "apy_asc":
        sort_text = "📉 APY ↑"
    row1.append(InlineKeyboardButton(text=sort_text, callback_data="sort_options"))

    product = filters.get("product")
    product_text = (
        f"🪙 {product}" if product else f"🪙 {localization.get_text('menu.product', lang)}"
    )
    row1.append(InlineKeyboardButton(text=product_text, callback_data="filter_product"))

    exchange = filters.get("exchange")
    exchange_text = (
        f"🏦 {exchange.title()}"
        if exchange
        else f"🏦 {localization.get_text('menu.exchange', lang)}"
    )
    row1.append(InlineKeyboardButton(text=exchange_text, callback_data="filter_exchange"))

    buttons.append(row1)

    buttons.append(
        [
            InlineKeyboardButton(
                text=f"♻️ {localization.get_text('menu.reset_filters', lang)}",
                callback_data="reset_filters",
            )
        ]
    )

    if show_pagination and total_pages > 1:
        nav_row = []
        if page > 1:
            nav_row.append(
                InlineKeyboardButton(
                    text=localization.get_text("nav.prev", lang),
                    callback_data=f"locked_prev:{page}",
                )
            )

        nav_row.append(InlineKeyboardButton(text=f"{page}/{total_pages}", callback_data="noop"))

        if page < total_pages:
            nav_row.append(
                InlineKeyboardButton(
                    text=localization.get_text("nav.next", lang),
                    callback_data=f"locked_next:{page}",
                )
            )

        buttons.append(nav_row)

    buttons.append(
        [
            InlineKeyboardButton(
                text=localization.get_text("nav.to_main", lang), callback_data="back_to_main"
            )
        ]
    )

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def all_products_keyboard(
    filters: Dict,
    page: int = 1,
    total_pages: int = 1,
    show_pagination: bool = True,
    lang: str = "ua",
) -> InlineKeyboardMarkup:
    buttons = []

    row1 = []

    sort_by = filters.get("sort_by", "popularity")
    sort_text = f"📊 {localization.get_text('menu.sort', lang)}"
    if sort_by == "apy_desc":
        sort_text = "📈 APY ↓"
    elif sort_by == "apy_asc":
        sort_text = "📉 APY ↑"
    row1.append(InlineKeyboardButton(text=sort_text, callback_data="sort_options"))

    product = filters.get("product")
    product_text = (
        f"🪙 {product}" if product else f"🪙 {localization.get_text('menu.product', lang)}"
    )
    row1.append(InlineKeyboardButton(text=product_text, callback_data="filter_product"))

    exchange = filters.get("exchange")
    exchange_text = (
        f"🏦 {exchange.title()}"
        if exchange
        else f"🏦 {localization.get_text('menu.exchange', lang)}"
    )
    row1.append(InlineKeyboardButton(text=exchange_text, callback_data="filter_exchange"))

    buttons.append(row1)

    buttons.append(
        [
            InlineKeyboardButton(
                text=f"♻️ {localization.get_text('menu.reset_filters', lang)}",
                callback_data="reset_filters",
            )
        ]
    )

    if show_pagination and total_pages > 1:
        nav_row = []
        if page > 1:
            nav_row.append(
                InlineKeyboardButton(
                    text=localization.get_text("nav.prev", lang), callback_data=f"all_prev:{page}"
                )
            )

        nav_row.append(InlineKeyboardButton(text=f"{page}/{total_pages}", callback_data="noop"))

        if page < total_pages:
            nav_row.append(
                InlineKeyboardButton(
                    text=localization.get_text("nav.next", lang), callback_data=f"all_next:{page}"
                )
            )

        buttons.append(nav_row)

    buttons.append(
        [
            InlineKeyboardButton(
                text=localization.get_text("nav.to_main", lang), callback_data="back_to_main"
            )
        ]
    )

    return InlineKeyboardMarkup(inline_keyboard=buttons)
