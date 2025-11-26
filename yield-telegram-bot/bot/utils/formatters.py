"""
Форматування таблиць та тексту для Telegram бота.

Забезпечує:
- Monospace таблиці з продуктами
- Адаптивне форматування APY
- Підтримка Flexible/Locked типів
- Екранування HTML для безпечного відображення
"""

from typing import List, Dict, Any
from bot.utils.logger import logger
from bot.localization import localization


def _escape_html(text: str) -> str:
    """
    Екранувати HTML спеціальні символи для безпечного відображення в Telegram.
    
    Args:
        text: Текст для екранування
        
    Returns:
        Екранований текст
    """
    if not isinstance(text, str):
        text = str(text)
    return (text
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;"))


def format_products_table(products: List[Dict[str, Any]], max_width: int = 50, lang: str = "ua") -> str:
    """
    Створює таблицю продуктів в monospace форматі.
    """
    if not products:
        return localization.get_text("table.empty", lang)

    # Розділити продукти на Flexible та Locked
    flexible = [p for p in products if p.get("lock_period_days", 0) == 0]
    locked = [p for p in products if p.get("lock_period_days", 0) > 0]

    # Створити таблицю
    result = "<pre>"

    # Заголовок
    h_flex = localization.get_text("table.product.flexible", lang).ljust(16)
    h_lock = localization.get_text("table.product.locked", lang)
    result += f"{h_flex}  {h_lock}\n"
    result += "━━━━━━━━━━━━━━━━  ━━━━━━━━━━━━━━━━━━━━━━\n"

    # Знайти максимальну кількість рядків
    max_rows = max(len(flexible), len(locked))

    for i in range(max_rows):
        # Flexible колонка
        if i < len(flexible):
            product = flexible[i]
            symbol = product.get("symbol", "???")[:7].ljust(7)
            apy = format_apy(product.get("apy", 0))
            flex_part = f"📊 {symbol}•{apy}"
        else:
            flex_part = "                    "

        # Locked колонка
        if i < len(locked):
            product = locked[i]
            symbol = product.get("symbol", "???")[:7].ljust(7)
            apy = format_apy(product.get("apy", 0))
            days = product.get("lock_period_days", 0)
            locked_part = f"📊 {symbol}•{apy}({days}d)"
        else:
            locked_part = "                         "

        result += f"{flex_part}  {locked_part}\n"

    result += "</pre>"

    return result


def format_apy(apy: float, width: int = 6) -> str:
    """
    Форматувати APY з адаптивною точністю.
    """
    if apy >= 1:
        return f"{apy:.1f}%".rjust(width)
    elif apy >= 0.1:
        return f"{apy:.2f}%".rjust(width)
    elif apy >= 0.01:
        return f"{apy:.3f}%".rjust(width)
    else:
        return f"{apy:.4f}%".rjust(width)


def format_exchange_product_table(products: List[Dict[str, Any]], page: int = 1, items_per_page: int = 50, total_products: int = 0, lang: str = "ua") -> str:
    """
    Форматувати таблицю продуктів однієї біржі з пагінацією.
    """
    if not products:
        return localization.get_text("table.empty", lang)

    page_products = products

    if not page_products:
        return localization.get_text("error.empty_page", lang)

    result = "<pre>"
    h_num = localization.get_text("table.header.number", lang)
    h_prod = localization.get_text("table.header.product", lang)
    h_apy = localization.get_text("table.header.apy", lang)
    h_type = localization.get_text("table.header.type", lang)
    h_per = localization.get_text("table.header.period", lang)
    
    result += f"{h_num}  {h_prod}  {h_apy}     {h_type}       {h_per}\n"
    result += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"

    start_idx = (page - 1) * items_per_page
    for i, product in enumerate(page_products, start_idx + 1):
        num = str(i).rjust(2)
        # Екранувати HTML у символі продукту (може містити теги з API)
        raw_symbol = product.get("symbol", "???")
        symbol = _escape_html(raw_symbol)[:7].ljust(7)
        apy = format_apy(product.get("apy", 0), 6)

        lock_days = product.get("lock_period_days", 0)
        product_type = "Flexible" if lock_days == 0 else "Locked"
        # Localize type if needed, but "Flexible"/"Locked" are standard terms usually kept or transliterated
        # Using localization keys for content might be too long for table.
        # Sticking to English terms or short localized versions if defined.
        # Tables.json has "table.product.flexible": "Flexible"

        type_str = localization.get_text(f"table.product.{product_type.lower()}", lang)
        if len(type_str) > 8: type_str = type_str[:8]
        type_str = type_str.ljust(9)

        if lock_days > 0:
            period = f"{lock_days}d"
        else:
            period = "—"

        result += f"{num} {symbol} {apy} {type_str} {period}\n"

    result += "</pre>"

    actual_total_products = total_products if total_products > 0 else len(products)
    shown_products = min(page * items_per_page, actual_total_products)
    total_pages = (actual_total_products + items_per_page - 1) // items_per_page

    result += f"\n📊 {localization.get_text('table.results.shown', lang, shown=shown_products, total=actual_total_products)} ({localization.get_text('nav.page', lang)} {page}/{total_pages})"

    return result


def format_product_comparison_table(products: List[Dict[str, Any]], lang: str = "ua") -> str:
    """
    Створити порівняльну таблицю продуктів з різних бірж.
    """
    if not products:
        return localization.get_text("table.empty", lang)

    result = "<pre>"
    h_exch = localization.get_text("table.header.exchange", lang)
    h_type = localization.get_text("table.header.type", lang)
    h_apy = localization.get_text("table.header.apy", lang)
    h_per = localization.get_text("table.header.period", lang)
    
    result += f"{h_exch}    {h_type}       {h_apy}     {h_per}\n"
    result += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"

    for product in products[:20]:
        provider = product.get("provider", "???")[:8].ljust(8)
        lock_days = product.get("lock_period_days", 0)
        product_type = "Flexible" if lock_days == 0 else "Locked"

        type_str = localization.get_text(f"table.product.{product_type.lower()}", lang)
        if len(type_str) > 8: type_str = type_str[:8]
        type_str = type_str.ljust(9)

        apy = format_apy(product.get("apy", 0), 6)

        if lock_days > 0:
            period = f"{lock_days}d"
        else:
            period = "—"

        result += f"{provider} {type_str} {apy}  {period}\n"

    result += "</pre>"
    return result


def format_flexible_products_table(products: List[Dict[str, Any]], page: int = 1, items_per_page: int = 50, total_products: int = 0, lang: str = "ua") -> str:
    """
    Форматувати таблицю Flexible продуктів з усіх бірж.
    """
    if not products:
        return localization.get_text("table.empty", lang)

    page_products = products
    if not page_products:
        return localization.get_text("error.empty_page", lang)
    
    result = "<pre>"
    h_prod = localization.get_text("table.header.product", lang)
    h_exch = localization.get_text("table.header.exchange", lang)
    h_apy = localization.get_text("table.header.apy", lang)
    
    result += f"{h_prod}  {h_exch}     {h_apy}\n"
    result += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    
    for product in page_products:
        symbol = product.get("symbol", "???")[:7].ljust(7)
        provider = product.get("provider", "???")[:9].ljust(9)
        apy = format_apy(product.get("apy", 0), 6)
        
        result += f"{symbol} {provider} {apy}\n"
    
    result += "</pre>"

    actual_total_products = total_products if total_products > 0 else len(products)
    shown_products = min(page * items_per_page, actual_total_products)
    total_pages = (actual_total_products + items_per_page - 1) // items_per_page

    result += f"\n📊 {localization.get_text('table.results.shown', lang, shown=shown_products, total=actual_total_products)} ({localization.get_text('nav.page', lang)} {page}/{total_pages})"

    return result


def format_all_products_table(products: List[Dict[str, Any]], page: int = 1, items_per_page: int = 50, total_products: int = 0, lang: str = "ua") -> str:
    """
    Форматувати таблицю всіх продуктів з усіх бірж (Flexible + Locked).
    """
    if not products:
        return localization.get_text("table.empty", lang)

    page_products = products
    if not page_products:
        return localization.get_text("error.empty_page", lang)

    result = "<pre>"
    h_prod = localization.get_text("table.header.product", lang)
    h_exch = localization.get_text("table.header.exchange", lang)
    h_apy = localization.get_text("table.header.apy", lang)
    h_type = localization.get_text("table.header.type", lang)
    h_per = localization.get_text("table.header.period", lang)
    
    result += f"{h_prod}  {h_exch}     {h_apy}     {h_type}       {h_per}\n"
    result += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"

    for product in page_products:
        symbol = str(product.get("symbol", "???"))[:7].ljust(7)
        provider = str(product.get("provider", "???"))[:9].ljust(9)

        apy_value = product.get("apy", 0)
        apy = f"{apy_value:.1f}%".ljust(6) if apy_value > 0 else "—".ljust(6)

        lock_period = product.get("lock_period_days", 0)
        product_type_key = "table.product.flexible" if lock_period == 0 else "table.product.locked"
        product_type = localization.get_text(product_type_key, lang)
        if len(product_type) > 8: product_type = product_type[:8]
        product_type = product_type.ljust(8)

        if lock_period > 0:
            if lock_period >= 365:
                years = lock_period // 365
                months = (lock_period % 365) // 30
                if months > 0:
                    period = f"{years}y{months}m"
                else:
                    period = f"{years}y"
            elif lock_period >= 30:
                months = lock_period // 30
                days = lock_period % 30
                if days > 0:
                    period = f"{months}m{days}d"
                else:
                    period = f"{months}m"
            else:
                period = f"{lock_period}d"
        else:
            period = "—"

        result += f"{symbol} {provider} {apy} {product_type} {period}\n"

    result += "</pre>"

    actual_total_products = total_products if total_products > 0 else len(products)
    shown_products = min(page * items_per_page, actual_total_products)
    total_pages = (actual_total_products + items_per_page - 1) // items_per_page

    result += f"\n📊 {localization.get_text('table.results.shown', lang, shown=shown_products, total=actual_total_products)} ({localization.get_text('nav.page', lang)} {page}/{total_pages})"

    return result


def format_locked_products_table(products: List[Dict[str, Any]], page: int = 1, items_per_page: int = 50, total_products: int = 0, lang: str = "ua") -> str:
    """
    Форматувати таблицю Locked продуктів з усіх бірж.
    """
    if not products:
        return localization.get_text("table.empty", lang)

    page_products = products
    if not page_products:
        return localization.get_text("error.empty_page", lang)

    result = "<pre>"
    h_prod = localization.get_text("table.header.product", lang)
    h_exch = localization.get_text("table.header.exchange", lang)
    h_apy = localization.get_text("table.header.apy", lang)
    h_per = localization.get_text("table.header.period", lang)
    
    result += f"{h_prod}  {h_exch}     {h_apy}     {h_per}\n"
    result += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"

    try:
        for product in page_products:
            symbol = product.get("symbol", "???")[:7].ljust(7)
            provider = product.get("provider", "???")[:9].ljust(9)
            apy = format_apy(product.get("apy", 0), 6)

            lock_days = product.get("lock_period_days", 0)
            if lock_days > 0:
                period = f"{lock_days}d"
            else:
                period = "—"

            result += f"{symbol} {provider} {apy}  {period}\n"
    except Exception as e:
        logger.error(f"Error in formatting locked products: {e}")
        result += f"Error\n"

    result += "</pre>"

    actual_total_products = total_products if total_products > 0 else len(products)
    shown_products = min(page * items_per_page, actual_total_products)
    total_pages = (actual_total_products + items_per_page - 1) // items_per_page

    result += f"\n📊 {localization.get_text('table.results.shown', lang, shown=shown_products, total=actual_total_products)} ({localization.get_text('nav.page', lang)} {page}/{total_pages})"

    return result
