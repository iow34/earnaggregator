"""
Клавіатури для фільтрів продуктів.

Забезпечує:
- Інтерактивні фільтри (продукт, біржа, тип)
- Сортування
- Скидання фільтрів
"""

from typing import Optional, List, Dict
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from bot.localization import localization


def filter_keyboard(
    current_filters: dict,
    show_reset: bool = True,
    show_sort: bool = True,
    lang: str = "ua"
) -> InlineKeyboardMarkup:
    """
    Створити клавіатуру з фільтрами.
    
    Args:
        current_filters: Поточні активні фільтри
        show_reset: Показати кнопку скидання
        show_sort: Показати кнопку сортування
        lang: Код мови
        
    Returns:
        Клавіатура з кнопками фільтрів
    """
    buttons = []
    
    # Рядок 1: Основні фільтри
    row1 = []
    
    # Фільтр по продукту
    product_text = f"🪙 {current_filters.get('product', localization.get_text('menu.product', lang))} ▼"
    row1.append(InlineKeyboardButton(
        text=product_text,
        callback_data="filter_product"
    ))
    
    # Фільтр по біржі
    exchange_val = current_filters.get('exchange')
    exchange_label = localization.get_text("menu.exchange", lang)
    exchange_text = f"🏦 {exchange_val.title() if exchange_val else exchange_label} ▼"
    row1.append(InlineKeyboardButton(
        text=exchange_text,
        callback_data="filter_exchange"
    ))
    
    buttons.append(row1)
    
    # Рядок 2: Додаткові фільтри
    row2 = []
    
    # Фільтр по типу
    type_val = current_filters.get('type')
    type_label = localization.get_text("menu.type", lang)
    type_text = f"⚡ {type_val.title() if type_val else type_label} ▼"
    row2.append(InlineKeyboardButton(
        text=type_text,
        callback_data="filter_type"
    ))
    
    # Фільтр по APY діапазону
    apy_text = f"📊 {localization.get_text('menu.apy', lang)} ▼"
    if current_filters.get('apy_min') or current_filters.get('apy_max'):
        apy_text = f"📊 {localization.get_text('menu.apy', lang)} ✓"
    row2.append(InlineKeyboardButton(
        text=apy_text,
        callback_data="filter_apy"
    ))
    
    buttons.append(row2)
    
    # Рядок 3: Сортування та скидання
    row3 = []
    
    if show_sort:
        sort_by = current_filters.get('sort_by', 'popularity')
        sort_text = f"📊 {localization.get_text('menu.sort', lang)}"
        if sort_by == "apy_desc":
            sort_text = "📈 APY ↓"
        elif sort_by == "apy_asc":
            sort_text = "📉 APY ↑"
        
        row3.append(InlineKeyboardButton(
            text=sort_text,
            callback_data="sort_options"
        ))
    
    if show_reset:
        row3.append(InlineKeyboardButton(
            text=f"♻️ {localization.get_text('menu.reset', lang)}",
            callback_data="reset_filters"
        ))
    
    if row3:
        buttons.append(row3)
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def product_selection_keyboard(
    products: List[str],
    current_product: Optional[str] = None,
    columns: int = 3,
    lang: str = "ua"
) -> InlineKeyboardMarkup:
    """
    Створити клавіатуру для вибору продукту.
    
    Args:
        products: Список доступних продуктів
        current_product: Поточно обраний продукт
        columns: Кількість колонок
        lang: Код мови
        
    Returns:
        Клавіатура з продуктами
    """
    buttons = []
    row = []
    
    for i, product in enumerate(products):
        # Додаємо галочку якщо це поточний продукт
        text = f"✓ {product}" if product == current_product else product
        
        row.append(InlineKeyboardButton(
            text=text,
            callback_data=f"select_product:{product}"
        ))
        
        # Створюємо новий рядок після досягнення columns
        if (i + 1) % columns == 0:
            buttons.append(row)
            row = []
    
    # Додаємо залишкові кнопки
    if row:
        buttons.append(row)
    
    # Кнопка "Назад"
    buttons.append([
        InlineKeyboardButton(
            text=localization.get_text("nav.back", lang),
            callback_data="back_to_filters"
        )
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def exchange_selection_keyboard(
    exchanges: List[str],
    current_exchange: Optional[str] = None,
    provider: Optional[str] = None,
    lang: str = "ua"
) -> InlineKeyboardMarkup:
    """
    Створити клавіатуру для вибору біржі.
    
    Args:
        exchanges: Список доступних бірж
        current_exchange: Поточно обрана біржа
        provider: Назва біржі для кнопки "Назад" (якщо є контекст)
        lang: Код мови
        
    Returns:
        Клавіатура з біржами
    """
    buttons = []
    
    for exchange in exchanges:
        text = f"✓ {exchange.title()}" if exchange == current_exchange else exchange.title()
        buttons.append([
            InlineKeyboardButton(
                text=text,
                callback_data=f"select_exchange:{exchange}"
            )
        ])
    
    # Кнопка "Всі біржі"
    buttons.append([
        InlineKeyboardButton(
            text=localization.get_text("nav.all_exchanges", lang),
            callback_data="select_exchange:all"
        )
    ])

    # Кнопка "Назад" з контекстом біржі або без нього
    if provider:
        buttons.append([
            InlineKeyboardButton(
                text=localization.get_text("nav.back", lang),
                callback_data=f"back_to_exchange:{provider}"
            )
        ])
    else:
        buttons.append([
            InlineKeyboardButton(
                text=localization.get_text("nav.back", lang),
                callback_data="back_to_filters"
            )
        ])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def type_selection_keyboard(
    current_type: Optional[str] = None, 
    provider: Optional[str] = None,
    lang: str = "ua"
) -> InlineKeyboardMarkup:
    """
    Створити клавіатуру для вибору типу продукту.
    
    Args:
        current_type: Поточно обраний тип
        provider: Назва біржі (якщо вибір робиться для конкретної біржі)
        lang: Код мови
        
    Returns:
        Клавіатура з типами
    """
    types = [
        ("flexible", localization.get_text("table.product.flexible", lang)),
        ("locked", localization.get_text("table.product.locked", lang)),
        ("all", localization.get_text("nav.all_types", lang))
    ]
    
    buttons = []
    for type_value, type_label in types:
        text = f"✓ {type_label}" if type_value == current_type else type_label
        
        # Якщо є provider, додаємо його до callback_data для збереження контексту
        callback_data = f"select_type:{type_value}:{provider}" if provider else f"select_type:{type_value}"
        
        buttons.append([
            InlineKeyboardButton(
                text=text,
                callback_data=callback_data
            )
        ])
    
    # Кнопка "Назад" з контекстом біржі або без нього
    if provider:
        back_callback = f"back_to_exchange:{provider}"
    else:
        back_callback = "back_to_filters"
    
    buttons.append([
        InlineKeyboardButton(
            text=localization.get_text("nav.back", lang),
            callback_data=back_callback
        )
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def sort_options_keyboard(
    current_sort: str = "popularity", 
    provider: str = "binance",
    lang: str = "ua"
) -> InlineKeyboardMarkup:
    """
    Створити клавіатуру для вибору сортування.

    Args:
        current_sort: Поточне сортування
        provider: Назва біржі для кнопки назад
        lang: Код мови

    Returns:
        Клавіатура з опціями сортування
    """
    options = [
        ("apy_desc", localization.get_text("menu.sort_apy_desc", lang)),
        ("apy_asc", localization.get_text("menu.sort_apy_asc", lang)),
        ("popularity", localization.get_text("menu.sort_popularity", lang))
    ]
    
    buttons = []
    for sort_value, sort_label in options:
        text = f"✓ {sort_label}" if sort_value == current_sort else sort_label

        buttons.append([
            InlineKeyboardButton(
                text=text,
                callback_data=f"sort:{sort_value}"
            )
        ])

    # Кнопка "Назад" - повернення до поточної сторінки
    buttons.append([
        InlineKeyboardButton(
            text=localization.get_text("nav.back", lang),
            callback_data="back_from_sort"
        )
    ])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def apy_range_keyboard(lang: str = "ua") -> InlineKeyboardMarkup:
    """
    Створити клавіатуру для вибору APY діапазону.
    
    Args:
        lang: Код мови
    
    Returns:
        Клавіатура з діапазонами APY
    """
    ranges = [
        ("0-5", "📊 0-5%"),
        ("5-10", "📈 5-10%"),
        ("10-20", "🔥 10-20%"),
        ("20+", "💥 20%+"),
        ("custom", f"✏️ {localization.get_text('menu.custom_range', lang)}")
    ]
    
    buttons = []
    for range_value, range_label in ranges:
        buttons.append([
            InlineKeyboardButton(
                text=range_label,
                callback_data=f"select_apy:{range_value}"
            )
        ])
    
    # Кнопка "Назад"
    buttons.append([
        InlineKeyboardButton(
            text=localization.get_text("nav.back", lang),
            callback_data="back_to_filters"
        )
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def create_exchange_filters_keyboard(
    provider: str, 
    current_filters: dict = None,
    lang: str = "ua"
) -> InlineKeyboardMarkup:
    """
    Створити клавіатуру фільтрів для конкретної біржі з динамічним сортуванням.

    Args:
        provider: Назва біржі (binance, bybit)
        current_filters: Поточні фільтри для відображення стану сортування
        lang: Код мови

    Returns:
        InlineKeyboardMarkup: Клавіатура з фільтрами (тільки сортування)
    """
    if current_filters is None:
        current_filters = {}

    # Визначаємо текст для кнопки сортування
    sort_by = current_filters.get('sort_by', 'popularity')
    sort_text = f"📊 {localization.get_text('menu.sort', lang)}"
    if sort_by == "apy_desc":
        sort_text = "📈 APY ↓"
    elif sort_by == "apy_asc":
        sort_text = "📉 APY ↑"

    buttons = [
        # Рядок тільки з сортуванням
        [
            InlineKeyboardButton(
                text=sort_text,
                callback_data=f"sort_options:{provider}"
            )
        ]
    ]

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def flexible_products_keyboard(
    filters: Dict,
    page: int = 1,
    total_pages: int = 1,
    show_pagination: bool = True,
    lang: str = "ua"
) -> InlineKeyboardMarkup:
    """
    Створити клавіатуру для сторінки Flexible products.
    
    Args:
        filters: Словник з поточними фільтрами
        page: Поточна сторінка
        total_pages: Загальна кількість сторінок
        show_pagination: Чи показувати пагінацію
        lang: Код мови
    
    Returns:
        InlineKeyboardMarkup: Клавіатура для сторінки Flexible products
    """
    buttons = []
    
    # Рядок 1: Фільтри
    row1 = []
    
    # Кнопка сортування
    sort_by = filters.get('sort_by', 'popularity')
    sort_text = f"📊 {localization.get_text('menu.sort', lang)}"
    if sort_by == "apy_desc":
        sort_text = "📈 APY ↓"
    elif sort_by == "apy_asc":
        sort_text = "📉 APY ↑"
    row1.append(InlineKeyboardButton(
        text=sort_text,
        callback_data="sort_options"
    ))
    
    # Кнопка вибору продукту
    product = filters.get('product')
    product_text = f"🪙 {product}" if product else f"🪙 {localization.get_text('menu.product', lang)}"
    row1.append(InlineKeyboardButton(
        text=product_text,
        callback_data="filter_product"
    ))
    
    # Кнопка вибору біржі
    exchange = filters.get('exchange')
    exchange_text = f"🏦 {exchange.title()}" if exchange else f"🏦 {localization.get_text('menu.exchange', lang)}"
    row1.append(InlineKeyboardButton(
        text=exchange_text,
        callback_data="filter_exchange"
    ))
    
    buttons.append(row1)
    
    # Рядок 2: Скинути фільтри
    buttons.append([
        InlineKeyboardButton(
            text=f"♻️ {localization.get_text('menu.reset_filters', lang)}",
            callback_data="reset_filters"
        )
    ])
    
    # Рядок 3: Пагінація
    if show_pagination and total_pages > 1:
        nav_row = []
        if page > 1:
            nav_row.append(InlineKeyboardButton(
                text=localization.get_text("nav.prev", lang),
                callback_data=f"flexible_prev:{page}"
            ))
        
        nav_row.append(InlineKeyboardButton(
            text=f"{page}/{total_pages}",
            callback_data="noop"
        ))
        
        if page < total_pages:
            nav_row.append(InlineKeyboardButton(
                text=localization.get_text("nav.next", lang),
                callback_data=f"flexible_next:{page}"
            ))
        
        buttons.append(nav_row)
    
    # Рядок 4: На головну
    buttons.append([
        InlineKeyboardButton(
            text=localization.get_text("nav.to_main", lang),
            callback_data="back_to_main"
        )
    ])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def locked_products_keyboard(
    filters: Dict,
    page: int = 1,
    total_pages: int = 1,
    show_pagination: bool = True,
    lang: str = "ua"
) -> InlineKeyboardMarkup:
    """
    Створити клавіатуру для сторінки Locked products.

    Args:
        filters: Словник з поточними фільтрами
        page: Поточна сторінка
        total_pages: Загальна кількість сторінок
        show_pagination: Чи показувати пагінацію
        lang: Код мови

    Returns:
        InlineKeyboardMarkup: Клавіатура для сторінки Locked products
    """
    buttons = []

    # Рядок 1: Фільтри
    row1 = []

    # Кнопка сортування
    sort_by = filters.get('sort_by', 'popularity')
    sort_text = f"📊 {localization.get_text('menu.sort', lang)}"
    if sort_by == "apy_desc":
        sort_text = "📈 APY ↓"
    elif sort_by == "apy_asc":
        sort_text = "📉 APY ↑"
    row1.append(InlineKeyboardButton(
        text=sort_text,
        callback_data="sort_options"
    ))

    # Кнопка вибору продукту
    product = filters.get('product')
    product_text = f"🪙 {product}" if product else f"🪙 {localization.get_text('menu.product', lang)}"
    row1.append(InlineKeyboardButton(
        text=product_text,
        callback_data="filter_product"
    ))

    # Кнопка вибору біржі
    exchange = filters.get('exchange')
    exchange_text = f"🏦 {exchange.title()}" if exchange else f"🏦 {localization.get_text('menu.exchange', lang)}"
    row1.append(InlineKeyboardButton(
        text=exchange_text,
        callback_data="filter_exchange"
    ))

    buttons.append(row1)

    # Рядок 2: Скинути фільтри
    buttons.append([
        InlineKeyboardButton(
            text=f"♻️ {localization.get_text('menu.reset_filters', lang)}",
            callback_data="reset_filters"
        )
    ])

    # Рядок 3: Пагінація
    if show_pagination and total_pages > 1:
        nav_row = []
        if page > 1:
            nav_row.append(InlineKeyboardButton(
                text=localization.get_text("nav.prev", lang),
                callback_data=f"locked_prev:{page}"
            ))

        nav_row.append(InlineKeyboardButton(
            text=f"{page}/{total_pages}",
            callback_data="noop"
        ))

        if page < total_pages:
            nav_row.append(InlineKeyboardButton(
                text=localization.get_text("nav.next", lang),
                callback_data=f"locked_next:{page}"
            ))

        buttons.append(nav_row)

    # Рядок 4: На головну
    buttons.append([
        InlineKeyboardButton(
            text=localization.get_text("nav.to_main", lang),
            callback_data="back_to_main"
        )
    ])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def all_products_keyboard(
    filters: Dict,
    page: int = 1,
    total_pages: int = 1,
    show_pagination: bool = True,
    lang: str = "ua"
) -> InlineKeyboardMarkup:
    """
    Створити клавіатуру для сторінки всіх продуктів.

    Args:
        filters: Словник з поточними фільтрами
        page: Поточна сторінка
        total_pages: Загальна кількість сторінок
        show_pagination: Чи показувати пагінацію
        lang: Код мови

    Returns:
        InlineKeyboardMarkup: Клавіатура для сторінки всіх продуктів
    """
    buttons = []

    # Рядок 1: Фільтри
    row1 = []

    # Кнопка сортування
    sort_by = filters.get('sort_by', 'popularity')
    sort_text = f"📊 {localization.get_text('menu.sort', lang)}"
    if sort_by == "apy_desc":
        sort_text = "📈 APY ↓"
    elif sort_by == "apy_asc":
        sort_text = "📉 APY ↑"
    row1.append(InlineKeyboardButton(
        text=sort_text,
        callback_data="sort_options"
    ))

    # Кнопка вибору продукту
    product = filters.get('product')
    product_text = f"🪙 {product}" if product else f"🪙 {localization.get_text('menu.product', lang)}"
    row1.append(InlineKeyboardButton(
        text=product_text,
        callback_data="filter_product"
    ))

    # Кнопка вибору біржі
    exchange = filters.get('exchange')
    exchange_text = f"🏦 {exchange.title()}" if exchange else f"🏦 {localization.get_text('menu.exchange', lang)}"
    row1.append(InlineKeyboardButton(
        text=exchange_text,
        callback_data="filter_exchange"
    ))

    buttons.append(row1)

    # Рядок 2: Скинути фільтри
    buttons.append([
        InlineKeyboardButton(
            text=f"♻️ {localization.get_text('menu.reset_filters', lang)}",
            callback_data="reset_filters"
        )
    ])

    # Рядок 3: Пагінація
    if show_pagination and total_pages > 1:
        nav_row = []
        if page > 1:
            nav_row.append(InlineKeyboardButton(
                text=localization.get_text("nav.prev", lang),
                callback_data=f"all_prev:{page}"
            ))

        nav_row.append(InlineKeyboardButton(
            text=f"{page}/{total_pages}",
            callback_data="noop"
        ))

        if page < total_pages:
            nav_row.append(InlineKeyboardButton(
                text=localization.get_text("nav.next", lang),
                callback_data=f"all_next:{page}"
            ))

        buttons.append(nav_row)

    # Рядок 4: На головну
    buttons.append([
        InlineKeyboardButton(
            text=localization.get_text("nav.to_main", lang),
            callback_data="back_to_main"
        )
    ])

    return InlineKeyboardMarkup(inline_keyboard=buttons)
