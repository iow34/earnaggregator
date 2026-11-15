import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from bot.content.recommendations import (
    load_recommendation,
    get_recommendations_menu,
    get_all_recommendation_ids,
    clear_cache,
)
from bot.handlers.recommendations import (
    create_recommendations_menu_keyboard,
    create_recommendation_detail_keyboard,
)


class TestContentLoader:
    def test_load_recommendation_ua(self):

        content = load_recommendation("rec1", "ua")

        assert content is not None
        assert isinstance(content, str)
        assert len(content) > 0
        assert "Переказ між біржами" in content or "переказ" in content.lower()

    def test_load_recommendation_invalid(self):

        content = load_recommendation("rec99", "ua")
        assert content is None

        content = load_recommendation("rec1", "invalid_lang")
        assert content is not None

    def test_get_recommendations_menu(self):
        menu = get_recommendations_menu("ua")

        assert isinstance(menu, dict)
        assert len(menu) == 10
        assert "rec1" in menu
        assert "rec10" in menu

        for rec_id, metadata in menu.items():
            assert "title" in metadata
            assert "emoji" in metadata

    def test_get_all_recommendation_ids(self):
        ids = get_all_recommendation_ids()

        assert isinstance(ids, list)
        assert len(ids) == 10
        assert "rec1" in ids
        assert "rec10" in ids

    def test_clear_cache(self):

        load_recommendation("rec1", "ua")

        clear_cache()

        content = load_recommendation("rec1", "ua")
        assert content is not None


class TestKeyboards:
    def test_create_recommendations_menu_keyboard(self):
        keyboard = create_recommendations_menu_keyboard()

        assert keyboard is not None
        assert hasattr(keyboard, "inline_keyboard")

        buttons = keyboard.inline_keyboard

        assert len(buttons) == 1

        assert buttons[0][0].callback_data == "back_to_main"

    def test_create_recommendation_detail_keyboard(self):

        keyboard = create_recommendation_detail_keyboard("rec1")

        assert keyboard is not None
        buttons = keyboard.inline_keyboard

        assert len(buttons) == 2

        assert buttons[0][0].callback_data == "back_to_recommendations"

        assert buttons[1][0].callback_data == "back_to_main"


@pytest.mark.asyncio
class TestHandlers:
    @pytest.mark.asyncio
    async def test_recommendation_detail_renders_localized_message(self):
        from bot.handlers.recommendations import show_recommendation_detail

        message = MagicMock(answer=AsyncMock())
        await show_recommendation_detail(message, "rec1", "en")
        kwargs = message.answer.call_args.kwargs
        assert kwargs["parse_mode"] == "HTML"
        assert kwargs["text"]
        assert kwargs["reply_markup"] is not None

    @pytest.mark.asyncio
    async def test_invalid_recommendation_returns_error(self):
        from bot.handlers.recommendations import show_recommendation_detail

        message = MagicMock(answer=AsyncMock())
        await show_recommendation_detail(message, "rec99", "en")
        message.answer.assert_awaited_once()
        assert "not found" in message.answer.call_args.args[0].lower()

    @pytest.mark.asyncio
    async def test_recommendations_menu_contains_all_commands(self):
        from bot.handlers.recommendations import show_recommendations_menu

        message = MagicMock(answer=AsyncMock())
        await show_recommendations_menu(message, "en")
        text = message.answer.call_args.kwargs["text"]
        assert all(f"/rec{i}" in text for i in range(1, 11))
