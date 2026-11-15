import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from aiogram.types import Message, User, Chat
from bot.middleware.first_contact import FirstContactMiddleware
from bot.content.welcome import get_welcome_message


class TestWelcomeMessageContent:
    def test_get_welcome_message_ua(self):
        message = get_welcome_message("ua")

        assert message is not None
        assert len(message) > 0
        assert "Вітаємо" in message
        assert "/start" in message
        assert "/help" in message
        assert "/start" in message
        assert "/help" in message

    def test_get_welcome_message_ru(self):
        message = get_welcome_message("ru")

        assert message is not None
        assert len(message) > 0
        assert "Добро пожаловать" in message
        assert "/start" in message
        assert "/help" in message

    def test_get_welcome_message_en(self):
        message = get_welcome_message("en")

        assert message is not None
        assert len(message) > 0
        assert "Welcome" in message
        assert "/start" in message
        assert "/help" in message

    def test_get_welcome_message_invalid_language_fallback(self):
        message = get_welcome_message("de")

        assert message is not None
        assert "Welcome" in message


class TestFirstContactMiddleware:
    @pytest.fixture
    def middleware(self):
        return FirstContactMiddleware()

    @pytest.fixture
    def mock_user(self):
        user = MagicMock(spec=User)
        user.id = 123456789
        user.language_code = "en"
        return user

    @pytest.fixture
    def mock_chat(self):
        chat = MagicMock(spec=Chat)
        chat.id = 123456789
        chat.type = "private"
        return chat

    @pytest.fixture
    def mock_message(self, mock_user, mock_chat):
        message = MagicMock(spec=Message)
        message.from_user = mock_user
        message.chat = mock_chat
        message.text = "Hello"
        message.answer = AsyncMock()
        return message

    @pytest.mark.asyncio
    async def test_middleware_handles_message_without_user(self, middleware):
        message = MagicMock(spec=Message)
        message.from_user = None

        handler = AsyncMock()
        data = {}

        await middleware(handler, message, data)

        handler.assert_called_once_with(message, data)

    @pytest.mark.asyncio
    async def test_middleware_skips_welcome_for_start_command(self, middleware, mock_message):
        mock_message.text = "/start"

        handler = AsyncMock()
        data = {}

        await middleware(handler, mock_message, data)

        handler.assert_called_once_with(mock_message, data)
        mock_message.answer.assert_not_called()

    @pytest.mark.asyncio
    async def test_middleware_sends_welcome_for_new_user(self, middleware, mock_message, mock_user):
        mock_message.text = "Hi"

        handler = AsyncMock()
        data = {}

        with patch("bot.middleware.first_contact.get_database_session") as mock_db:
            mock_session = AsyncMock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock()

            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = None
            mock_session.execute = AsyncMock(return_value=mock_result)

            mock_db.return_value = mock_session

            await middleware(handler, mock_message, data)

            mock_message.answer.assert_called_once()

            call_kwargs = mock_message.answer.call_args[1]
            assert call_kwargs["parse_mode"] == "HTML"

            handler.assert_called_once_with(mock_message, data)

    @pytest.mark.asyncio
    async def test_middleware_skips_welcome_for_existing_user(self, middleware, mock_message):
        mock_message.text = "Hi"

        handler = AsyncMock()
        data = {}

        with patch("bot.middleware.first_contact.get_database_session") as mock_db:
            mock_session = AsyncMock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock()

            mock_user_obj = MagicMock()
            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = mock_user_obj
            mock_session.execute = AsyncMock(return_value=mock_result)

            mock_db.return_value = mock_session

            await middleware(handler, mock_message, data)

            mock_message.answer.assert_not_called()

            handler.assert_called_once_with(mock_message, data)

    @pytest.mark.asyncio
    async def test_middleware_handles_errors_gracefully(self, middleware, mock_message):
        mock_message.text = "Hi"

        handler = AsyncMock()
        data = {}

        with patch("bot.middleware.first_contact.get_database_session") as mock_db:
            mock_db.side_effect = Exception("Database error")

            await middleware(handler, mock_message, data)

            handler.assert_called_once_with(mock_message, data)

    @pytest.mark.asyncio
    async def test_middleware_detects_language_from_telegram(
        self, middleware, mock_message, mock_user
    ):
        test_cases = [
            ("uk", "ua", "Вітаємо"),
            ("ru", "ru", "Добро пожаловать"),
            ("en", "en", "Welcome"),
        ]

        for tg_lang, expected_lang, expected_word in test_cases:
            mock_user.language_code = tg_lang
            mock_message.text = "Test"
            mock_message.answer = AsyncMock()

            handler = AsyncMock()
            data = {}

            with patch("bot.middleware.first_contact.get_database_session") as mock_db:
                mock_session = AsyncMock()
                mock_session.__aenter__ = AsyncMock(return_value=mock_session)
                mock_session.__aexit__ = AsyncMock()

                mock_result = MagicMock()
                mock_result.scalar_one_or_none.return_value = None
                mock_session.execute = AsyncMock(return_value=mock_result)

                mock_db.return_value = mock_session

                await middleware(handler, mock_message, data)

                call_args = mock_message.answer.call_args[0]
                assert expected_word in call_args[0]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
