"""
Unit тести для модуля рекомендацій (статична логіка).

Тестує:
- Завантаження текстів рекомендацій
- Створення клавіатур
- Обробники команд та callback
"""

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
    """Тести для content loader."""
    
    def test_load_recommendation_ua(self):
        """Тест завантаження української рекомендації."""
        # Тестуємо завантаження rec1
        content = load_recommendation("rec1", "ua")
        
        assert content is not None
        assert isinstance(content, str)
        assert len(content) > 0
        assert "Переказ між біржами" in content or "переказ" in content.lower()
    
    def test_load_recommendation_invalid(self):
        """Тест завантаження невалідної рекомендації."""
        # Невалідний rec_id
        content = load_recommendation("rec99", "ua")
        assert content is None
        
        # Невалідна мова (повинна fallback на ua)
        content = load_recommendation("rec1", "invalid_lang")
        assert content is not None
    
    def test_get_recommendations_menu(self):
        """Тест отримання меню рекомендацій."""
        menu = get_recommendations_menu("ua")
        
        assert isinstance(menu, dict)
        assert len(menu) == 10
        assert "rec1" in menu
        assert "rec10" in menu
        
        # Перевірка структури метаданих
        for rec_id, metadata in menu.items():
            assert "title" in metadata
            assert "emoji" in metadata
    
    def test_get_all_recommendation_ids(self):
        """Тест отримання всіх ID рекомендацій."""
        ids = get_all_recommendation_ids()
        
        assert isinstance(ids, list)
        assert len(ids) == 10
        assert "rec1" in ids
        assert "rec10" in ids
    
    def test_clear_cache(self):
        """Тест очищення кешу."""
        # Завантажуємо рекомендацію
        load_recommendation("rec1", "ua")
        
        # Очищуємо кеш
        clear_cache()
        
        # Кеш повинен бути очищений (перевіряємо що функція не падає)
        content = load_recommendation("rec1", "ua")
        assert content is not None


class TestKeyboards:
    """Тести для клавіатур."""
    
    def test_create_recommendations_menu_keyboard(self):
        """Тест створення клавіатури меню рекомендацій."""
        keyboard = create_recommendations_menu_keyboard()
        
        assert keyboard is not None
        assert hasattr(keyboard, "inline_keyboard")
        
        buttons = keyboard.inline_keyboard
        # Має бути тільки 1 кнопка "На головну"
        assert len(buttons) == 1
        
        # Перевірка кнопки "На головну"
        assert buttons[0][0].callback_data == "back_to_main"
    
    def test_create_recommendation_detail_keyboard(self):
        """Тест створення клавіатури деталей рекомендації."""
        # Перевірка для будь-якої рекомендації
        keyboard = create_recommendation_detail_keyboard("rec1")
        
        assert keyboard is not None
        buttons = keyboard.inline_keyboard
        
        # Має бути: "Назад до списку" + "На головну"
        assert len(buttons) == 2
        
        # Перевірка наявності кнопки "Назад до списку"
        assert buttons[0][0].callback_data == "back_to_recommendations"
        
        # Перевірка наявності кнопки "На головну"
        assert buttons[1][0].callback_data == "back_to_main"


@pytest.mark.asyncio
class TestHandlers:
    """Тести для handlers."""
    
    async def test_show_recommendations_menu(self):
        """Тест показу меню рекомендацій."""
        from bot.handlers.recommendations import show_recommendations_menu
        
        # Mock об'єктів
        message = MagicMock()
        message.from_user.id = 123456
        message.answer = AsyncMock()
        
        # Викликаємо функцію
        await show_recommendations_menu(message, "ua")
        
        # Перевірка
        message.answer.assert_called_once()
        call_args = message.answer.call_args
        
        assert "Рекомендації" in call_args.kwargs["text"]
        assert call_args.kwargs["parse_mode"] == "HTML"
        assert call_args.kwargs["reply_markup"] is not None
    
    async def test_show_recommendation_detail(self):
        """Тест показу деталей рекомендації."""
        from bot.handlers.recommendations import show_recommendation_detail
        
        # Mock об'єктів
        callback = MagicMock()
        callback.from_user.id = 123456
        callback.message.edit_text = AsyncMock()
        callback.answer = AsyncMock()
        
        # Викликаємо функцію для валідної рекомендації
        await show_recommendation_detail(callback, "rec1", "ua")
        
        # Перевірка
        callback.message.edit_text.assert_called_once()
        callback.answer.assert_called_once()
        
        call_args = callback.message.edit_text.call_args
        assert call_args.kwargs["parse_mode"] == "HTML"
        assert call_args.kwargs["reply_markup"] is not None
    
    async def test_show_recommendation_detail_invalid(self):
        """Тест показу неіснуючої рекомендації."""
        from bot.handlers.recommendations import show_recommendation_detail
        
        # Mock об'єктів
        callback = MagicMock()
        callback.from_user.id = 123456
        callback.answer = AsyncMock()
        
        # Викликаємо функцію для невалідної рекомендації
        await show_recommendation_detail(callback, "rec99", "ua")
        
        # Перевірка що викликано callback.answer з помилкою
        callback.answer.assert_called_once()
        call_args = callback.answer.call_args
        assert "не знайдена" in call_args.args[0] or "not found" in call_args.args[0].lower()
    
    @patch("bot.handlers.recommendations.get_or_create_user")
    @patch("bot.handlers.recommendations.add_user_query")
    @patch("bot.handlers.recommendations.get_database_session")
    async def test_recommendations_command_handler(
        self,
        mock_db_session,
        mock_add_query,
        mock_get_user
    ):
        """Тест обробника команди /recommendations."""
        from bot.handlers.recommendations import recommendations_command_handler
        
        # Mock БД
        mock_session = AsyncMock()
        mock_db_session.return_value.__aenter__.return_value = mock_session
        mock_get_user.return_value = MagicMock(id=1)
        mock_add_query.return_value = MagicMock()
        
        # Mock message
        message = MagicMock()
        message.from_user.id = 123456
        message.from_user.username = "testuser"
        message.from_user.first_name = "Test"
        message.from_user.last_name = "User"
        message.answer = AsyncMock()
        
        # Викликаємо handler
        await recommendations_command_handler(message)
        
        # Перевірка що БД операції викликані
        mock_get_user.assert_called_once()
        mock_add_query.assert_called_once()
        
        # Перевірка що повідомлення відправлено
        message.answer.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

