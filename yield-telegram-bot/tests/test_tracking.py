import pytest
import asyncio
from datetime import datetime, UTC
from unittest.mock import Mock, AsyncMock, patch


@pytest.mark.asyncio
async def test_session_creation():
    from bot.services.session_manager import SessionManager

    session_manager = SessionManager()

    # Mock Redis
    with patch("bot.services.session_manager.redis") as mock_redis:
        mock_redis_instance = AsyncMock()
        mock_redis.from_url.return_value = mock_redis_instance
        mock_redis_instance.ping = AsyncMock()
        mock_redis_instance.get = AsyncMock(return_value=None)
        mock_redis_instance.setex = AsyncMock()

        await session_manager.initialize()

        user_id = 12345
        session_id = await session_manager.get_or_create_session(user_id)

        assert session_id is not None
        assert len(session_id) == 36
        assert isinstance(session_id, str)


@pytest.mark.asyncio
async def test_session_reuse():
    from bot.services.session_manager import SessionManager

    session_manager = SessionManager()

    with patch("bot.services.session_manager.redis") as mock_redis:
        mock_redis_instance = AsyncMock()
        mock_redis.from_url.return_value = mock_redis_instance
        mock_redis_instance.ping = AsyncMock()

        existing_session = "test-session-123"
        mock_redis_instance.get = AsyncMock(return_value=existing_session)
        mock_redis_instance.expire = AsyncMock()

        await session_manager.initialize()

        user_id = 12345
        session_id = await session_manager.get_or_create_session(user_id)

        assert session_id == existing_session
        mock_redis_instance.expire.assert_called_once()


@pytest.mark.asyncio
async def test_event_tracking():
    from bot.services.event_processor import EventProcessor

    event_processor = EventProcessor()

    with patch("bot.services.event_processor.redis") as mock_redis:
        mock_redis_instance = AsyncMock()
        mock_redis.from_url.return_value = mock_redis_instance
        mock_redis_instance.ping = AsyncMock()
        mock_redis_instance.xgroup_create = AsyncMock()
        mock_redis_instance.xadd = AsyncMock(return_value=b"1234-0")

        await event_processor.initialize()

        event_data = {
            "user_id": 12345,
            "action_type": "command_start",
            "session_id": "test-session-id",
            "context": {"command": "/start"},
            "platform": "telegram",
        }

        success = await event_processor.add_event(event_data)
        assert success is True
        mock_redis_instance.xadd.assert_called_once()


@pytest.mark.asyncio
async def test_event_context_serialization():
    from bot.services.event_processor import EventProcessor

    event_processor = EventProcessor()

    with patch("bot.services.event_processor.redis") as mock_redis:
        mock_redis_instance = AsyncMock()
        mock_redis.from_url.return_value = mock_redis_instance
        mock_redis_instance.ping = AsyncMock()
        mock_redis_instance.xgroup_create = AsyncMock()
        mock_redis_instance.xadd = AsyncMock(return_value=b"1234-0")

        await event_processor.initialize()

        event_data = {
            "user_id": 12345,
            "action_type": "button_click",
            "session_id": "test-session-id",
            "context": {"callback_data": "filter_product:BTC", "category": "filter"},
            "platform": "telegram",
        }

        success = await event_processor.add_event(event_data)
        assert success is True


@pytest.mark.asyncio
async def test_tracking_middleware_message():
    from bot.middleware.tracking import TrackingMiddleware
    from aiogram.types import Message, User, Chat, Update

    middleware = TrackingMiddleware()

    user = User(id=12345, is_bot=False, first_name="Test")
    chat = Chat(id=12345, type="private")
    message = Message(
        message_id=1, date=datetime.now(UTC), chat=chat, from_user=user, text="/start"
    )
    update = Update(update_id=1, message=message)

    # Mock handler
    handler = AsyncMock(return_value=None)
    data = {}

    with patch("bot.middleware.tracking.session_manager") as mock_session_manager:
        with patch("bot.middleware.tracking.event_processor") as mock_event_processor:
            mock_session_manager.get_or_create_session = AsyncMock(return_value="test-session")
            mock_event_processor.add_event = AsyncMock(return_value=True)

            await middleware(handler, update, data)

            handler.assert_called_once()

            mock_event_processor.add_event.assert_called_once()

            call_args = mock_event_processor.add_event.call_args[0][0]
            assert call_args["user_id"] == 12345
            assert call_args["action_type"] == "command_start"
            assert call_args["session_id"] == "test-session"


@pytest.mark.asyncio
async def test_tracking_middleware_callback():
    from bot.middleware.tracking import TrackingMiddleware
    from aiogram.types import CallbackQuery, User, Message, Chat, Update

    middleware = TrackingMiddleware()

    user = User(id=12345, is_bot=False, first_name="Test")
    chat = Chat(id=12345, type="private")
    message = Message(message_id=1, date=datetime.now(UTC), chat=chat)
    callback = CallbackQuery(
        id="callback123",
        from_user=user,
        chat_instance="test",
        data="filter_product:BTC",
        message=message,
    )
    update = Update(update_id=1, callback_query=callback)

    handler = AsyncMock(return_value=None)
    data = {}

    with patch("bot.middleware.tracking.session_manager") as mock_session_manager:
        with patch("bot.middleware.tracking.event_processor") as mock_event_processor:
            mock_session_manager.get_or_create_session = AsyncMock(return_value="test-session")
            mock_event_processor.add_event = AsyncMock(return_value=True)

            await middleware(handler, update, data)

            handler.assert_called_once()
            mock_event_processor.add_event.assert_called_once()

            call_args = mock_event_processor.add_event.call_args[0][0]
            assert call_args["action_type"] == "button_click"
            assert "callback_data" in call_args["context"]


@pytest.mark.asyncio
async def test_log_cleaner():
    from bot.schedulers.log_cleaner import LogCleaner

    cleaner = LogCleaner()

    await cleaner.start()
    assert cleaner.running is True
    assert cleaner.task is not None

    await cleaner.stop()
    assert cleaner.running is False


@pytest.mark.asyncio
async def test_batch_processing_performance():
    from bot.services.event_processor import EventProcessor

    event_processor = EventProcessor()

    with patch("bot.services.event_processor.redis") as mock_redis:
        mock_redis_instance = AsyncMock()
        mock_redis.from_url.return_value = mock_redis_instance
        mock_redis_instance.ping = AsyncMock()
        mock_redis_instance.xgroup_create = AsyncMock()
        mock_redis_instance.xadd = AsyncMock(return_value=b"1234-0")

        await event_processor.initialize()

        start_time = datetime.now(UTC)

        for i in range(100):
            event_data = {
                "user_id": 12345 + i,
                "action_type": "command_start",
                "session_id": f"test-session-{i}",
                "context": {"command": "/start"},
                "platform": "telegram",
            }
            await event_processor.add_event(event_data)

        end_time = datetime.now(UTC)
        duration = (end_time - start_time).total_seconds()

        assert duration < 1.0
        assert mock_redis_instance.xadd.call_count == 100


def test_action_type_detection():
    from bot.middleware.tracking import TrackingMiddleware
    from aiogram.types import Message, User, Chat

    middleware = TrackingMiddleware()

    user = User(id=1, is_bot=False, first_name="Test")
    chat = Chat(id=1, type="private")

    message_start = Message(
        message_id=1, date=datetime.now(UTC), chat=chat, from_user=user, text="/start"
    )
    assert middleware._get_message_action_type(message_start) == "command_start"

    message_yield = Message(
        message_id=2, date=datetime.now(UTC), chat=chat, from_user=user, text="/yield BTC"
    )
    assert middleware._get_message_action_type(message_yield) == "command_yield"

    message_text = Message(
        message_id=3, date=datetime.now(UTC), chat=chat, from_user=user, text="Hello"
    )
    assert middleware._get_message_action_type(message_text) == "text_input"


def test_context_extraction():
    from bot.middleware.tracking import TrackingMiddleware
    from aiogram.types import Message, User, Chat, CallbackQuery

    middleware = TrackingMiddleware()

    user = User(id=1, is_bot=False, first_name="Test")
    chat = Chat(id=1, type="private")

    message = Message(
        message_id=1, date=datetime.now(UTC), chat=chat, from_user=user, text="/yield BTC"
    )
    context = middleware._extract_message_context(message)
    assert context["command"] == "/yield"
    assert context["args"] == "BTC"

    msg = Message(message_id=1, date=datetime.now(UTC), chat=chat)
    callback = CallbackQuery(
        id="1", from_user=user, chat_instance="test", data="filter_product:BTC", message=msg
    )
    context = middleware._extract_callback_context(callback)
    assert context["callback_data"] == "filter_product:BTC"
    assert context["category"] == "filter"
