"""
Утиліта для пагінації списків продуктів.

Забезпечує:
- Розбиття великих списків на сторінки
- Генерацію навігаційних кнопок
- Підтримку до 30 елементів на сторінку
"""

import math
from typing import List, Any
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from bot.localization import localization


class Paginator:
    """Клас для управління пагінацією елементів."""
    
    def __init__(self, items: List[Any], items_per_page: int = 30):
        """
        Ініціалізація пагінатора.
        
        Args:
            items: Список елементів для пагінації
            items_per_page: Кількість елементів на сторінку (макс 60 для Telegram)
        """
        self.items = items
        self.items_per_page = min(items_per_page, 60)  # Telegram обмеження на символи (4096), таблиця з 60 продуктами ~2000 символів
        self.total_pages = math.ceil(len(items) / self.items_per_page) if items else 0
    
    def get_page(self, page: int) -> List[Any]:
        """
        Отримати елементи конкретної сторінки.
        
        Args:
            page: Номер сторінки (починається з 1)
            
        Returns:
            Список елементів для сторінки
        """
        if page < 1 or page > self.total_pages:
            return []
        
        start = (page - 1) * self.items_per_page
        end = start + self.items_per_page
        return self.items[start:end]
    
    def get_navigation_keyboard(
        self,
        page: int,
        callback_prefix: str,
        extra_buttons: List[List[InlineKeyboardButton]] = None,
        lang: str = "ua"
    ) -> InlineKeyboardMarkup:
        """
        Створити клавіатуру навігації для пагінації.
        
        Args:
            page: Поточна сторінка
            callback_prefix: Префікс для callback_data (напр. "products")
            extra_buttons: Додаткові кнопки (напр. "Назад")
            
        Returns:
            Клавіатура з кнопками навігації
        """
        buttons = []
        
        # Рядок з навігацією по сторінкам
        nav_row = []
        if page > 1:
            nav_row.append(
                InlineKeyboardButton(
                    text=localization.get_text("nav.previous", lang),
                    callback_data=f"{callback_prefix}_prev:{page}"
                )
            )
        
        # Показуємо поточну сторінку
        nav_row.append(
            InlineKeyboardButton(
                text=f"{page}/{self.total_pages}",
                callback_data="noop"  # Неактивна кнопка
            )
        )
        
        if page < self.total_pages:
            nav_row.append(
                InlineKeyboardButton(
                    text=localization.get_text("nav.next", lang),
                    callback_data=f"{callback_prefix}_next:{page}"
                )
            )
        
        if nav_row:
            buttons.append(nav_row)
        
        # Додаємо extra кнопки якщо є
        if extra_buttons:
            buttons.extend(extra_buttons)
        
        return InlineKeyboardMarkup(inline_keyboard=buttons)
    
    def has_next_page(self, page: int) -> bool:
        """Перевірити чи є наступна сторінка."""
        return page < self.total_pages
    
    def has_prev_page(self, page: int) -> bool:
        """Перевірити чи є попередня сторінка."""
        return page > 1

