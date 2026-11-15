import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage

from bot.handlers.main_menu import (
    exchanges_command_handler,
    _display_all_exchanges,
    all_exchanges_handler,
)
from bot.keyboards.reply import main_menu


class TestExchangesCommand:
    @pytest.mark.asyncio
    async def test_exchanges_command_handler(self):
        message = MagicMock()
        message.from_user.id = 123456
        message.text = "/exchanges"
        message.answer = AsyncMock(return_value=MagicMock(message_id=1, edit_text=AsyncMock()))

        storage = MemoryStorage()
        state = FSMContext(storage=storage, key=MagicMock())

        await exchanges_command_handler(message, state)

        assert message.answer.called

        data = await state.get_data()
        assert data.get("current_page") == "all_exchanges"
        assert data.get("lang") == "ua"
        assert data.get("page") == 1

    @pytest.mark.asyncio
    async def test_exchanges_button_handler(self):
        message = MagicMock()
        message.from_user.id = 654321
        message.text = "🏦 Exchanges"
        message.answer = AsyncMock(return_value=MagicMock(message_id=2, edit_text=AsyncMock()))

        storage = MemoryStorage()
        state = FSMContext(storage=storage, key=MagicMock())

        await exchanges_command_handler(message, state)

        assert message.answer.called

        data = await state.get_data()
        assert data.get("current_page") == "all_exchanges"

    @pytest.mark.asyncio
    async def test_exchanges_multilanguage(self):

        for lang in ["ua", "en", "ru"]:
            message = MagicMock()
            message.from_user.id = 111111
            message.text = "/exchanges"
            message.answer = AsyncMock(return_value=MagicMock(message_id=3, edit_text=AsyncMock()))

            storage = MemoryStorage()
            state = FSMContext(storage=storage, key=MagicMock())

            await state.update_data(lang=lang)

            await exchanges_command_handler(message, state)

            data = await state.get_data()
            assert data.get("lang") == lang

    @pytest.mark.asyncio
    async def test_all_exchanges_callback(self):
        callback = MagicMock()
        callback.from_user.id = 789012
        callback.data = "all_exchanges"
        callback.answer = AsyncMock()
        callback.message = MagicMock()
        callback.message.answer = AsyncMock(
            return_value=MagicMock(message_id=4, edit_text=AsyncMock())
        )
        callback.message.delete = AsyncMock()
        callback.message.message_id = 100

        storage = MemoryStorage()
        state = FSMContext(storage=storage, key=MagicMock())

        await all_exchanges_handler(callback, state)

        assert callback.answer.called


class TestExchangesKeyboard:
    def test_main_menu_has_exchanges_button(self):
        from bot.localization import localization

        for lang in ("ua", "ru", "en"):
            labels = [button.text for row in main_menu(lang).keyboard for button in row]
            assert localization.get_menu_text("menu.main.exchanges", lang) in labels

    def test_main_menu_structure(self):
        kb = main_menu(lang="en")
        assert [len(row) for row in kb.keyboard] == [2, 2]
        assert kb.resize_keyboard is True
        assert len({button.text for row in kb.keyboard for button in row}) == 4

    def test_main_menu_backwards_compatibility(self):
        kb_default = main_menu()
        kb_ua = main_menu(lang="ua")

        assert len(kb_default.keyboard) == len(kb_ua.keyboard)

        for i, row in enumerate(kb_default.keyboard):
            assert len(row) == len(kb_ua.keyboard[i])


class TestExchangesMultilanguage:
    def test_language_texts_structure(self):

        texts = {
            "ua": {
                "title": "🏦 <b>Всі біржі</b>\n\n",
                "go_to": "перейти ↗️",
                "shown": "Показано",
                "of": "з",
                "exchanges": "бірж",
                "page": "сторінка",
            },
            "en": {
                "title": "🏦 <b>All Exchanges</b>\n\n",
                "go_to": "visit ↗️",
                "shown": "Shown",
                "of": "of",
                "exchanges": "exchanges",
                "page": "page",
            },
            "ru": {
                "title": "🏦 <b>Все биржи</b>\n\n",
                "go_to": "перейти ↗️",
                "shown": "Показано",
                "of": "из",
                "exchanges": "бирж",
                "page": "страница",
            },
        }

        required_keys = ["title", "go_to", "shown", "of", "exchanges", "page"]

        for lang, lang_texts in texts.items():
            for key in required_keys:
                assert key in lang_texts, f"Ключ {key} відсутній для мови {lang}"

    def test_language_fallback(self):
        from bot.localization import localization

        kb = main_menu(lang="unknown_language")
        expected = localization.get_menu_text("menu.main.exchanges", "unknown_language")
        assert expected in [b.text for row in kb.keyboard for b in row]


class TestExchangesIntegration:
    @pytest.mark.asyncio
    async def test_full_flow(self):
        message = MagicMock()
        message.from_user.id = 999999
        message.text = "/exchanges"
        message.answer = AsyncMock(return_value=MagicMock(message_id=1, edit_text=AsyncMock()))

        storage = MemoryStorage()
        state = FSMContext(storage=storage, key=MagicMock())

        await state.update_data(lang="en")

        await exchanges_command_handler(message, state)

        data = await state.get_data()

        assert data.get("current_page") == "all_exchanges"
        assert data.get("lang") == "en"
        assert data.get("page") == 1
        assert message.answer.called

    @pytest.mark.asyncio
    async def test_tracking_middleware_integration(self):
        from bot.middleware.tracking import TrackingMiddleware

        middleware = TrackingMiddleware()

        message = MagicMock()
        message.text = "/exchanges"

        action_type = middleware._get_message_action_type(message)

        assert action_type == "command_exchanges"
