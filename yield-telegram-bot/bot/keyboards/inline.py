from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from bot.localization import localization


def referral_buttons(
    binance_url: str | None = None, bybit_url: str | None = None, lang: str = "ua"
) -> InlineKeyboardMarkup:
    buttons = []
    # Exchange names are usually not translated, but we could if we wanted.
    # For now keeping them as is.
    if binance_url:
        buttons.append([InlineKeyboardButton(text="Binance", url=binance_url)])
    if bybit_url:
        buttons.append([InlineKeyboardButton(text="Bybit", url=bybit_url)])

    # Fallback button if no URLs provided
    if not buttons:
        buttons.append(
            [
                InlineKeyboardButton(
                    text=localization.get_text("nav.visit", lang), url="https://example.com"
                )
            ]
        )

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def pagination(prev_cb: str | None, next_cb: str | None, lang: str = "ua") -> InlineKeyboardMarkup:
    row = []
    if prev_cb:
        row.append(
            InlineKeyboardButton(
                text=localization.get_text("nav.previous", lang), callback_data=prev_cb
            )
        )
    if next_cb:
        row.append(
            InlineKeyboardButton(
                text=localization.get_text("nav.next", lang), callback_data=next_cb
            )
        )
    return InlineKeyboardMarkup(inline_keyboard=[row] if row else [])


def get_back_to_list_keyboard(callback_data: str, lang: str = "ua") -> InlineKeyboardMarkup:
    """Keyboard with just 'Back to list' button."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=localization.get_text("nav.back_to_list", lang),
                    callback_data=callback_data,
                )
            ]
        ]
    )
