from typing import Optional, List
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from bot.localization import localization


def main_menu_navigation(lang: str = "ua") -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton(
                text=localization.get_text("nav.show_all_products", lang),
                callback_data="all_products",
            ),
            InlineKeyboardButton(
                text=localization.get_text("nav.all_exchanges", lang), callback_data="all_exchanges"
            ),
        ],
        [
            InlineKeyboardButton(
                text=localization.get_text("table.product.flexible", lang),
                callback_data="type_flexible",
            ),
            InlineKeyboardButton(
                text=localization.get_text("table.product.locked", lang),
                callback_data="type_locked",
            ),
        ],
        [
            InlineKeyboardButton(
                text=localization.get_text("menu.advanced_search", lang),
                callback_data="advanced_search",
            )
        ],
    ]

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def exchange_menu_keyboard(
    provider: str, referral_url: Optional[str] = None, show_filters: bool = True, lang: str = "ua"
) -> InlineKeyboardMarkup:
    buttons = []

    if referral_url:
        buttons.append(
            [
                InlineKeyboardButton(
                    text=localization.get_text(
                        "nav.go_to_exchange", lang, exchange=provider.title()
                    ),
                    url=referral_url,
                )
            ]
        )

    row = []
    row.append(
        InlineKeyboardButton(
            text=localization.get_text("nav.all_products", lang),
            callback_data=f"show_all:{provider}",
        )
    )

    if show_filters:
        row.append(
            InlineKeyboardButton(
                text=localization.get_text("menu.filter", lang), callback_data=f"filters:{provider}"
            )
        )

    buttons.append(row)

    buttons.append(
        [
            InlineKeyboardButton(
                text=localization.get_text("nav.to_main", lang), callback_data="back_to_main"
            )
        ]
    )

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def product_details_keyboard(
    provider: str,
    product_id: str,
    referral_url: Optional[str] = None,
    show_compare: bool = False,
    lang: str = "ua",
) -> InlineKeyboardMarkup:
    buttons = []

    if referral_url:
        buttons.append(
            [
                InlineKeyboardButton(
                    text=localization.get_text(
                        "nav.go_to_exchange", lang, exchange=provider.title()
                    ),
                    url=referral_url,
                )
            ]
        )

    row = []
    if show_compare:
        row.append(
            InlineKeyboardButton(
                text=localization.get_text("nav.compare", lang),
                callback_data=f"compare:{product_id}",
            )
        )

    row.append(
        InlineKeyboardButton(
            text=localization.get_text("nav.other_products", lang),
            callback_data=f"show_all:{provider}",
        )
    )

    if row:
        buttons.append(row)

    buttons.append(
        [
            InlineKeyboardButton(
                text=localization.get_text("nav.back_to_list", lang), callback_data="back_to_list"
            )
        ]
    )

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def back_button_keyboard(
    callback_data: str = "back_to_main",
    text: str = None,  # Changed default to None to allow dynamic loading if not provided
    lang: str = "ua",
) -> InlineKeyboardMarkup:
    if text is None:
        # Determine text based on callback data or just use generic "Back"
        if callback_data == "back_to_main":
            text = localization.get_text("nav.to_main", lang)
        else:
            text = localization.get_text("nav.back", lang)

    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=text, callback_data=callback_data)]]
    )


def exchange_list_keyboard(exchanges: List[dict], lang: str = "ua") -> InlineKeyboardMarkup:
    buttons = []

    for exchange in exchanges:
        name = exchange.get("name", "").title()
        count = exchange.get("count", 0)

        buttons.append(
            [
                InlineKeyboardButton(
                    text=localization.get_text(
                        "nav.exchange_products_count", lang, exchange=name, count=count
                    ),
                    callback_data=f"exchange_menu:{exchange['name']}",
                )
            ]
        )

    buttons.append(
        [
            InlineKeyboardButton(
                text=localization.get_text("nav.to_main", lang), callback_data="back_to_main"
            )
        ]
    )

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def quick_actions_keyboard(symbol: str, lang: str = "ua") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=localization.get_text("nav.best_apy", lang),
                    callback_data=f"best_apy:{symbol}",
                ),
                InlineKeyboardButton(
                    text=localization.get_text("table.product.flexible", lang),
                    callback_data=f"flexible:{symbol}",
                ),
            ],
            [
                InlineKeyboardButton(
                    text=localization.get_text("table.product.locked", lang),
                    callback_data=f"locked:{symbol}",
                ),
                InlineKeyboardButton(
                    text=localization.get_text("nav.compare_exchanges", lang),
                    callback_data=f"compare_exchanges:{symbol}",
                ),
            ],
            [
                InlineKeyboardButton(
                    text=localization.get_text("nav.to_main", lang), callback_data="back_to_main"
                )
            ],
        ]
    )


def refresh_button_keyboard(
    callback_data: str = "refresh_data", lang: str = "ua"
) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=localization.get_text("nav.refresh_data", lang),
                    callback_data=callback_data,
                )
            ],
            [
                InlineKeyboardButton(
                    text=localization.get_text("nav.back", lang), callback_data="back_to_main"
                )
            ],
        ]
    )


def disclaimer_keyboard(lang: str = "en") -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton(
                text=localization.get_text("nav.go_to_main", lang), callback_data="go_to_main"
            )
        ]
    ]

    return InlineKeyboardMarkup(inline_keyboard=buttons)
