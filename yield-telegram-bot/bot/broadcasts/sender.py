"""
Сервіс надсилання повідомлень для ручних розсилок.
"""

from __future__ import annotations

from typing import Iterable, Optional

from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message


class BroadcastSender:
    """Обгортка над Bot для надсилання контенту розсилки."""

    def __init__(self, bot: Bot) -> None:
        self._bot = bot

    async def send_message(
        self,
        *,
        telegram_id: int,
        content_payload: dict,
        content_type: str,
    ) -> Message:
        markup = self._build_keyboard(content_payload.get("buttons", []))
        parse_mode = content_payload.get("parse_mode")
        disable_preview = content_payload.get("disable_link_preview", False)
        text = content_payload.get("text")

        if content_type in {"text", "markdown", "html"}:
            return await self._bot.send_message(
                chat_id=telegram_id,
                text=text or "",
                parse_mode=parse_mode,
                reply_markup=markup,
                disable_web_page_preview=disable_preview,
            )

        if content_type == "photo":
            media = content_payload.get("media_file_id") or content_payload.get("media_url")
            return await self._bot.send_photo(
                chat_id=telegram_id,
                photo=media,
                caption=text,
                parse_mode=parse_mode,
                reply_markup=markup,
            )

        if content_type == "document":
            media = content_payload.get("media_file_id") or content_payload.get("media_url")
            return await self._bot.send_document(
                chat_id=telegram_id,
                document=media,
                caption=text,
                parse_mode=parse_mode,
                reply_markup=markup,
            )

        raise ValueError(f"Unsupported content_type: {content_type}")

    def _build_keyboard(self, buttons: Iterable[dict]) -> Optional[InlineKeyboardMarkup]:
        rows = []
        for button in buttons or []:
            text = button.get("text")
            url = button.get("url")
            callback_data = button.get("callback_data")
            if not text:
                continue
            if not url and not callback_data:
                continue
            rows.append(
                [
                    InlineKeyboardButton(
                        text=text,
                        url=url,
                        callback_data=callback_data,
                    )
                ]
            )

        if not rows:
            return None

        return InlineKeyboardMarkup(inline_keyboard=rows)

