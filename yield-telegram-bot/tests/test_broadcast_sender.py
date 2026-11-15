from unittest.mock import AsyncMock

import pytest
from aiogram import Bot

from bot.broadcasts.sender import BroadcastSender


@pytest.mark.asyncio
async def test_sender_sends_text_message(monkeypatch):
    bot = AsyncMock(spec=Bot)
    bot.send_message.return_value = AsyncMock(message_id=10)
    sender = BroadcastSender(bot=bot)

    result = await sender.send_message(
        telegram_id=123,
        content_payload={
            "text": "Hello",
            "parse_mode": "HTML",
            "buttons": [],
            "disable_link_preview": False,
        },
        content_type="text",
    )

    bot.send_message.assert_awaited_once()
    assert result.message_id == 10


@pytest.mark.asyncio
async def test_sender_sends_photo(monkeypatch):
    bot = AsyncMock(spec=Bot)
    bot.send_photo.return_value = AsyncMock(message_id=20)
    sender = BroadcastSender(bot=bot)

    payload = {
        "text": "Caption",
        "media_file_id": "photo123",
        "buttons": [],
    }
    result = await sender.send_message(
        telegram_id=321,
        content_payload=payload,
        content_type="photo",
    )

    bot.send_photo.assert_awaited_once()
    assert result.message_id == 20
