from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from bot.localization import localization

def main_menu(lang: str = "ua") -> ReplyKeyboardMarkup:
    """
    Створити головне меню з підтримкою мультимовності.
    
    Args:
        lang: Код мови (ua, en, ru)
        
    Returns:
        ReplyKeyboardMarkup з кнопками
    """
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text=localization.get_menu_text("menu.main.language", lang)),
                KeyboardButton(text=localization.get_menu_text("menu.main.exchanges", lang))
            ],
            [
                KeyboardButton(text=localization.get_menu_text("menu.main.recommendations", lang)),
                KeyboardButton(text=localization.get_menu_text("menu.main.help", lang))
            ],
        ],
        resize_keyboard=True,
        input_field_placeholder=localization.get_menu_text("menu.main.placeholder", lang),
    )
