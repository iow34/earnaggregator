from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock
import pytest
from bot.handlers import language


@pytest.mark.asyncio
async def test_language_selection_uses_stored_language(monkeypatch):
    @asynccontextmanager
    async def session():
        yield object()

    monkeypatch.setattr(language.db_manager, "get_session", session)
    monkeypatch.setattr(
        language, "get_or_create_user", AsyncMock(return_value=MagicMock(language="en"))
    )
    message = MagicMock()
    message.answer = AsyncMock()
    state = AsyncMock()
    await language.language_handler(message, state)
    state.update_data.assert_awaited_once_with(language="en")
    state.set_state.assert_awaited_once_with(language.LanguageSelection.waiting_for_language)
    assert len(message.answer.call_args.kwargs["reply_markup"].inline_keyboard) == 4


@pytest.mark.asyncio
async def test_database_failure_returns_localized_error(monkeypatch):
    @asynccontextmanager
    async def session():
        raise RuntimeError("Unavailable")
        yield

    monkeypatch.setattr(language.db_manager, "get_session", session)
    message = MagicMock()
    message.answer = AsyncMock()
    await language.language_handler(message, AsyncMock())
    message.answer.assert_awaited_once()
    assert message.answer.call_args.args[0] == language.localization.get_error_text(
        "error.general", "ua"
    )
