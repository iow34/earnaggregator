import math
from typing import List, Any
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from bot.localization import localization


class Paginator:
    def __init__(self, items: List[Any], items_per_page: int = 30):
        self.items = items
        self.items_per_page = max(1, min(items_per_page, 60))
        self.total_pages = math.ceil(len(items) / self.items_per_page) if items else 0

    def get_page(self, page: int) -> List[Any]:
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
        lang: str = "ua",
    ) -> InlineKeyboardMarkup:
        buttons = []

        nav_row = []
        if page > 1:
            nav_row.append(
                InlineKeyboardButton(
                    text=localization.get_text("nav.previous", lang),
                    callback_data=f"{callback_prefix}_prev:{page}",
                )
            )

        nav_row.append(
            InlineKeyboardButton(text=f"{page}/{self.total_pages}", callback_data="noop")
        )

        if page < self.total_pages:
            nav_row.append(
                InlineKeyboardButton(
                    text=localization.get_text("nav.next", lang),
                    callback_data=f"{callback_prefix}_next:{page}",
                )
            )

        if nav_row:
            buttons.append(nav_row)

        if extra_buttons:
            buttons.extend(extra_buttons)

        return InlineKeyboardMarkup(inline_keyboard=buttons)

    def has_next_page(self, page: int) -> bool:
        return page < self.total_pages

    def has_prev_page(self, page: int) -> bool:
        return page > 1
