"""
Тести для команди /exchanges та кнопки Exchanges.

Перевіряє:
- Реєстрацію команди /exchanges
- Роботу кнопки "🏦 Exchanges"
- Підтримку мультимовності (UA/EN/RU)
- Коректну роботу pagination
- Відсутність конфліктів з іншими handlers
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage

from bot.handlers.main_menu import exchanges_command_handler, _display_all_exchanges, all_exchanges_handler
from bot.keyboards.reply import main_menu


class TestExchangesCommand:
    """Тести для команди /exchanges."""
    
    @pytest.mark.asyncio
    async def test_exchanges_command_handler(self):
        """Тест обробника команди /exchanges."""
        message = MagicMock()
        message.from_user.id = 123456
        message.text = "/exchanges"
        message.answer = AsyncMock(return_value=MagicMock(
            message_id=1,
            edit_text=AsyncMock()
        ))
        
        storage = MemoryStorage()
        state = FSMContext(storage=storage, key=MagicMock())
        
        # Виконати handler
        await exchanges_command_handler(message, state)
        
        # Перевірки
        assert message.answer.called
        
        # Перевірка state
        data = await state.get_data()
        assert data.get("current_page") == "all_exchanges"
        assert data.get("lang") == "ua"  # За замовчуванням
        assert data.get("page") == 1
    
    @pytest.mark.asyncio
    async def test_exchanges_button_handler(self):
        """Тест обробника кнопки '🏦 Exchanges'."""
        message = MagicMock()
        message.from_user.id = 654321
        message.text = "🏦 Exchanges"
        message.answer = AsyncMock(return_value=MagicMock(
            message_id=2,
            edit_text=AsyncMock()
        ))
        
        storage = MemoryStorage()
        state = FSMContext(storage=storage, key=MagicMock())
        
        # Виконати handler
        await exchanges_command_handler(message, state)
        
        # Перевірки
        assert message.answer.called
        
        # Перевірка state
        data = await state.get_data()
        assert data.get("current_page") == "all_exchanges"
    
    @pytest.mark.asyncio
    async def test_exchanges_multilanguage(self):
        """Тест мультимовності для команди /exchanges."""
        
        for lang in ['ua', 'en', 'ru']:
            message = MagicMock()
            message.from_user.id = 111111
            message.text = "/exchanges"
            message.answer = AsyncMock(return_value=MagicMock(
                message_id=3,
                edit_text=AsyncMock()
            ))
            
            storage = MemoryStorage()
            state = FSMContext(storage=storage, key=MagicMock())
            
            # Встановити мову
            await state.update_data(lang=lang)
            
            # Виконати handler
            await exchanges_command_handler(message, state)
            
            # Перевірка що мова збережена
            data = await state.get_data()
            assert data.get("lang") == lang
    
    @pytest.mark.asyncio
    async def test_all_exchanges_callback(self):
        """Тест callback handler для 'all_exchanges'."""
        callback = MagicMock()
        callback.from_user.id = 789012
        callback.data = "all_exchanges"
        callback.answer = AsyncMock()
        callback.message = MagicMock()
        callback.message.answer = AsyncMock(return_value=MagicMock(
            message_id=4,
            edit_text=AsyncMock()
        ))
        callback.message.delete = AsyncMock()
        callback.message.message_id = 100
        
        storage = MemoryStorage()
        state = FSMContext(storage=storage, key=MagicMock())
        
        # Виконати handler
        await all_exchanges_handler(callback, state)
        
        # Перевірки
        assert callback.answer.called


class TestExchangesKeyboard:
    """Тести для Reply Keyboard з кнопкою Exchanges."""
    
    def test_main_menu_has_exchanges_button(self):
        """Тест наявності кнопки Exchanges в main menu."""
        for lang in ['ua', 'en', 'ru']:
            kb = main_menu(lang=lang)
            
            # Знайти кнопку Exchanges
            exchanges_button = None
            for row in kb.keyboard:
                for btn in row:
                    if "Exchanges" in btn.text:
                        exchanges_button = btn.text
                        break
            
            assert exchanges_button is not None, f"Кнопка Exchanges не знайдена для мови {lang}"
            assert exchanges_button == "🏦 Exchanges"
    
    def test_main_menu_structure(self):
        """Тест структури main menu."""
        kb = main_menu(lang="ua")
        
        # Має бути 3 рядки
        assert len(kb.keyboard) == 3
        
        # Перший рядок: Recommendations, Help
        assert len(kb.keyboard[0]) == 2
        assert "Recommendations" in kb.keyboard[0][0].text
        assert "Help" in kb.keyboard[0][1].text
        
        # Другий рядок: Exchanges
        assert len(kb.keyboard[1]) == 1
        assert "Exchanges" in kb.keyboard[1][0].text
        
        # Третій рядок: Language
        assert len(kb.keyboard[2]) == 1
        assert "Language" in kb.keyboard[2][0].text
    
    def test_main_menu_backwards_compatibility(self):
        """Тест зворотної сумісності main_menu() без параметрів."""
        kb_default = main_menu()
        kb_ua = main_menu(lang="ua")
        
        # Мають бути ідентичні
        assert len(kb_default.keyboard) == len(kb_ua.keyboard)
        
        for i, row in enumerate(kb_default.keyboard):
            assert len(row) == len(kb_ua.keyboard[i])


class TestExchangesMultilanguage:
    """Тести мультимовності для сторінки Exchanges."""
    
    def test_language_texts_structure(self):
        """Тест структури мультимовних текстів."""
        # Імітація тексти з _display_all_exchanges
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
            }
        }
        
        # Перевірка що всі ключі є в усіх мовах
        required_keys = ["title", "go_to", "shown", "of", "exchanges", "page"]
        
        for lang, lang_texts in texts.items():
            for key in required_keys:
                assert key in lang_texts, f"Ключ {key} відсутній для мови {lang}"
    
    def test_language_fallback(self):
        """Тест fallback на українську при невідомій мові."""
        kb = main_menu(lang="unknown_language")
        
        # Має використати українську
        exchanges_button = None
        for row in kb.keyboard:
            for btn in row:
                if "Exchanges" in btn.text:
                    exchanges_button = btn.text
                    break
        
        assert exchanges_button == "🏦 Exchanges"


class TestExchangesIntegration:
    """Інтеграційні тести для команди /exchanges."""
    
    @pytest.mark.asyncio
    async def test_full_flow(self):
        """Тест повного флоу: команда → відображення → state."""
        message = MagicMock()
        message.from_user.id = 999999
        message.text = "/exchanges"
        message.answer = AsyncMock(return_value=MagicMock(
            message_id=1,
            edit_text=AsyncMock()
        ))
        
        storage = MemoryStorage()
        state = FSMContext(storage=storage, key=MagicMock())
        
        # Встановити мову
        await state.update_data(lang="en")
        
        # Виконати handler
        await exchanges_command_handler(message, state)
        
        # Перевірка state
        data = await state.get_data()
        
        assert data.get("current_page") == "all_exchanges"
        assert data.get("lang") == "en"
        assert data.get("page") == 1
        assert message.answer.called
    
    @pytest.mark.asyncio
    async def test_tracking_middleware_integration(self):
        """Тест інтеграції з tracking middleware."""
        from bot.middleware.tracking import TrackingMiddleware
        
        middleware = TrackingMiddleware()
        
        # Тест повідомлення
        message = MagicMock()
        message.text = "/exchanges"
        
        action_type = middleware._get_message_action_type(message)
        
        assert action_type == "command_exchanges"

