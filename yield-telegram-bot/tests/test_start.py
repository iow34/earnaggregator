"""
Тести для start handler та disclaimer функцій.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from bot.handlers.start import show_disclaimer_page, go_to_main_handler


@pytest.mark.asyncio
async def test_show_disclaimer_page():
    """Тест відображення disclaimer сторінки."""
    # Mock message та state
    message = AsyncMock()
    message.from_user = AsyncMock()
    message.from_user.language_code = "en"
    message.answer = AsyncMock()

    state = AsyncMock()
    state.update_data = AsyncMock()

    # Викликаємо функцію
    await show_disclaimer_page(message, state, "en")

    # Перевіряємо що повідомлення було надіслано
    message.answer.assert_called_once()
    call_args = message.answer.call_args

    # Перевіряємо що текст містить disclaimer елементи
    text = call_args[0][0]
    assert "Chain Advisor" in text
    assert "crypto analytics bot" in text
    assert "No financial advice" in text
    assert "parse_mode" in call_args[1]
    assert call_args[1]["parse_mode"] == "HTML"

    # Перевіряємо що стан було оновлено
    state.update_data.assert_called_once_with(current_page="disclaimer", lang="en")


@pytest.mark.asyncio
async def test_go_to_main_handler():
    """Тест обробки кнопки Go to main."""
    # Mock callback та message
    callback = AsyncMock()
    callback.message = AsyncMock()
    callback.message.from_user = AsyncMock()
    callback.message.from_user.id = 12345
    callback.message.answer = AsyncMock()

    state = AsyncMock()
    state.get_data = AsyncMock(return_value={"lang": "en"})

    # Mock loading message
    loading_message = AsyncMock()
    callback.message.answer.return_value = loading_message

    # Mock show_main_page
    with pytest.mock.patch('bot.handlers.start.show_main_page') as mock_show_main_page:
        # Викликаємо функцію
        await go_to_main_handler(callback, state)

        # Перевіряємо що callback було підтверджено
        callback.answer.assert_called_once()

        # Перевіряємо що loading message було надіслано
        callback.message.answer.assert_called_once()

        # Перевіряємо що show_main_page було викликано
        mock_show_main_page.assert_called_once_with(callback.message, state, "en")

        # Перевіряємо що loading message було видалено
        loading_message.delete.assert_called_once()


@pytest.mark.asyncio
async def test_go_to_main_handler_error():
    """Тест обробки помилки в go_to_main_handler."""
    # Mock callback та message
    callback = AsyncMock()
    callback.message = AsyncMock()
    callback.message.from_user = AsyncMock()
    callback.message.from_user.id = 12345
    callback.message.answer = AsyncMock()

    state = AsyncMock()
    state.get_data = AsyncMock(return_value={"lang": "en"})

    # Mock show_main_page щоб викликати помилку
    with pytest.mock.patch('bot.handlers.start.show_main_page', side_effect=Exception("Test error")):
        # Викликаємо функцію
        await go_to_main_handler(callback, state)

        # Перевіряємо що було два виклики answer (loading + error)
        assert callback.message.answer.call_count == 2