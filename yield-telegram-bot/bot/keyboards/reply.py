from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from bot.localization import localization


def main_menu(lang: str = "ua") -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text=localization.get_menu_text("menu.main.language", lang)),
                KeyboardButton(text=localization.get_menu_text("menu.main.exchanges", lang)),
            ],
            [
                KeyboardButton(text=localization.get_menu_text("menu.main.recommendations", lang)),
                KeyboardButton(text=localization.get_menu_text("menu.main.help", lang)),
            ],
        ],
        resize_keyboard=True,
        input_field_placeholder=localization.get_menu_text("menu.main.placeholder", lang),
    )
