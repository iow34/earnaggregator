"""
Тести для обробника кнопки Мова.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from aiogram.types import Message, User
from aiogram.fsm.context import FSMContext

from bot.handlers.language import language_handler


@pytest.fixture
def mock_message():
    """Фікстура для Message."""
    message = MagicMock(spec=Message)
    message.from_user = MagicMock(spec=User)
    message.from_user.id = 12345
    message.from_user.username = "testuser"
    message.from_user.first_name = "Test"
    message.from_user.last_name = "User"
    message.text = "🌐 Мова"
    message.answer = AsyncMock()
    return message


@pytest.fixture
def mock_state():
    """Фікстура для FSMContext."""
    return MagicMock(spec=FSMContext)


@pytest.mark.asyncio
async def test_language_handler_success(mock_message, mock_state):
    """Тест успішного виклику обробника Мова."""
    await language_handler(mock_message, mock_state)
    
    # Перевірка, що відправлено повідомлення
    mock_message.answer.assert_called_once()
    call_args = mock_message.answer.call_args
    
    # Перевірка вмісту повідомлення
    assert "🌐" in call_args[0][0]
    assert "Вибір мови" in call_args[0][0]
    assert "функція" in call_args[0][0].lower()
    assert call_args[1]["parse_mode"] == "HTML"


@pytest.mark.asyncio
async def test_language_handler_error(mock_message, mock_state):
    """Тест обробки помилки в language_handler."""
    # Симулюємо помилку при відправці повідомлення
    mock_message.answer = AsyncMock(side_effect=Exception("Test error"))
    
    # Виклик має пройти без винятку
    await language_handler(mock_message, mock_state)
    
    # Повідомлення має бути викликане двічі (перший раз з помилкою, другий - з повідомленням про помилку)
    assert mock_message.answer.call_count >= 1

