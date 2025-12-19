"""
Навігаційні клавіатури для переміщення між сторінками.

Забезпечує:
- Навігацію між головним меню та підменю
- Кнопки "Назад"
- Швидкі переходи до розділів
"""

from typing import Optional, List
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from bot.localization import localization


def main_menu_navigation(lang: str = "ua") -> InlineKeyboardMarkup:
    """
    Створити навігацію для головного меню.
    
    Returns:
        Клавіатура з кнопками навігації
    """
    buttons = [
        [
            InlineKeyboardButton(
                text=localization.get_text("nav.show_all_products", lang),
                callback_data="all_products"
            ),
            InlineKeyboardButton(
                text=localization.get_text("nav.all_exchanges", lang),
                callback_data="all_exchanges"
            )
        ],
        [
            InlineKeyboardButton(
                text=localization.get_text("table.product.flexible", lang),
                callback_data="type_flexible"
            ),
            InlineKeyboardButton(
                text=localization.get_text("table.product.locked", lang),
                callback_data="type_locked"
            )
        ],
        [
            InlineKeyboardButton(
                text=localization.get_text("menu.advanced_search", lang),
                callback_data="advanced_search"
            )
        ]
    ]
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def exchange_menu_keyboard(
    provider: str,
    referral_url: Optional[str] = None,
    show_filters: bool = True,
    lang: str = "ua"
) -> InlineKeyboardMarkup:
    """
    Створити меню для конкретної біржі.
    
    Args:
        provider: Назва біржі
        referral_url: Реферальне посилання
        show_filters: Показати кнопку фільтрів
        lang: Код мови
        
    Returns:
        Клавіатура з опціями біржі
    """
    buttons = []
    
    # Реферальне посилання
    if referral_url:
        buttons.append([
            InlineKeyboardButton(
                text=localization.get_text("nav.go_to_exchange", lang, exchange=provider.title()),
                url=referral_url
            )
        ])
    
    # Рядок з опціями
    row = []
    row.append(InlineKeyboardButton(
        text=localization.get_text("nav.all_products", lang),
        callback_data=f"show_all:{provider}"
    ))
    
    if show_filters:
        row.append(InlineKeyboardButton(
            text=localization.get_text("menu.filter", lang),
            callback_data=f"filters:{provider}"
        ))
    
    buttons.append(row)
    
    # Кнопка "Назад"
    buttons.append([
        InlineKeyboardButton(
            text=localization.get_text("nav.to_main", lang),
            callback_data="back_to_main"
        )
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def product_details_keyboard(
    provider: str,
    product_id: str,
    referral_url: Optional[str] = None,
    show_compare: bool = False,
    lang: str = "ua"
) -> InlineKeyboardMarkup:
    """
    Створити клавіатуру для сторінки деталей продукту.
    
    Args:
        provider: Назва біржі
        product_id: ID продукту
        referral_url: Реферальне посилання
        show_compare: Показати кнопку порівняння
        lang: Код мови
        
    Returns:
        Клавіатура з опціями продукту
    """
    buttons = []
    
    # Реферальне посилання
    if referral_url:
        buttons.append([
            InlineKeyboardButton(
                text=localization.get_text("nav.go_to_exchange", lang, exchange=provider.title()),
                url=referral_url
            )
        ])
    
    # Опції
    row = []
    if show_compare:
        row.append(InlineKeyboardButton(
            text=localization.get_text("nav.compare", lang),
            callback_data=f"compare:{product_id}"
        ))
    
    row.append(InlineKeyboardButton(
        text=localization.get_text("nav.other_products", lang),
        callback_data=f"show_all:{provider}"
    ))
    
    if row:
        buttons.append(row)
    
    # Кнопка "Назад"
    buttons.append([
        InlineKeyboardButton(
            text=localization.get_text("nav.back_to_list", lang),
            callback_data="back_to_list"
        )
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def back_button_keyboard(
    callback_data: str = "back_to_main",
    text: str = None,  # Changed default to None to allow dynamic loading if not provided
    lang: str = "ua"
) -> InlineKeyboardMarkup:
    """
    Створити клавіатуру тільки з кнопкою "Назад".
    
    Args:
        callback_data: Callback для кнопки назад
        text: Текст кнопки (якщо None, завантажується з локалізації)
        lang: Код мови
        
    Returns:
        Клавіатура з кнопкою назад
    """
    if text is None:
        # Determine text based on callback data or just use generic "Back"
        if callback_data == "back_to_main":
            text = localization.get_text("nav.to_main", lang)
        else:
            text = localization.get_text("nav.back", lang)
            
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=text, callback_data=callback_data)]
    ])


def exchange_list_keyboard(exchanges: List[dict], lang: str = "ua") -> InlineKeyboardMarkup:
    """
    Створити клавіатуру зі списком бірж.
    
    Args:
        exchanges: Список бірж з інформацією
            [{"name": "binance", "count": 50, "referral_url": "..."}, ...]
        lang: Код мови
        
    Returns:
        Клавіатура з біржами
    """
    buttons = []
    
    for exchange in exchanges:
        name = exchange.get("name", "").title()
        count = exchange.get("count", 0)
        
        buttons.append([
            InlineKeyboardButton(
                text=localization.get_text("nav.exchange_products_count", lang, exchange=name, count=count),
                callback_data=f"exchange_menu:{exchange['name']}"
            )
        ])
    
    # Кнопка "Назад"
    buttons.append([
        InlineKeyboardButton(
            text=localization.get_text("nav.to_main", lang),
            callback_data="back_to_main"
        )
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def quick_actions_keyboard(symbol: str, lang: str = "ua") -> InlineKeyboardMarkup:
    """
    Створити клавіатуру зі швидкими діями для продукту.
    
    Args:
        symbol: Символ криптовалюти
        lang: Код мови
        
    Returns:
        Клавіатура зі швидкими діями
    """
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text=localization.get_text("nav.best_apy", lang),
                callback_data=f"best_apy:{symbol}"
            ),
            InlineKeyboardButton(
                text=localization.get_text("table.product.flexible", lang),
                callback_data=f"flexible:{symbol}"
            )
        ],
        [
            InlineKeyboardButton(
                text=localization.get_text("table.product.locked", lang),
                callback_data=f"locked:{symbol}"
            ),
            InlineKeyboardButton(
                text=localization.get_text("nav.compare_exchanges", lang),
                callback_data=f"compare_exchanges:{symbol}"
            )
        ],
        [
            InlineKeyboardButton(
                text=localization.get_text("nav.to_main", lang),
                callback_data="back_to_main"
            )
        ]
    ])


def refresh_button_keyboard(callback_data: str = "refresh_data", lang: str = "ua") -> InlineKeyboardMarkup:
    """
    Створити клавіатуру з кнопкою оновлення.
    
    Args:
        callback_data: Callback для кнопки оновлення
        lang: Код мови
        
    Returns:
        Клавіатура з кнопкою оновлення
    """
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text=localization.get_text("nav.refresh_data", lang),
                callback_data=callback_data
            )
        ],
        [
            InlineKeyboardButton(
                text=localization.get_text("nav.back", lang),
                callback_data="back_to_main"
            )
        ]
    ])


def disclaimer_keyboard(lang: str = "en") -> InlineKeyboardMarkup:
    """
    Створити клавіатуру для disclaimer сторінки.

    Args:
        lang: Код мови

    Returns:
        Клавіатура з кнопкою "Go to main"
    """
    buttons = [
        [InlineKeyboardButton(
            text=localization.get_text("nav.go_to_main", lang),
            callback_data="go_to_main"
        )]
    ]

    return InlineKeyboardMarkup(inline_keyboard=buttons)
