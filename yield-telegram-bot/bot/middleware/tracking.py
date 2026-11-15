import time
from typing import Any, Callable, Dict, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import Update, Message, CallbackQuery
from bot.services.event_processor import event_processor
from bot.services.session_manager import session_manager
from bot.utils.logger import logger

try:
    from bot.utils.metrics import Counter, Histogram, registry

    TRACKING_EVENTS_TOTAL = Counter(
        "telegram_bot_tracking_events_total",
        "Загальна кількість трекінгових подій",
        ["action_type"],
        registry=registry,
    )

    TRACKING_LATENCY = Histogram(
        "telegram_bot_tracking_latency_seconds",
        "Час запису події в чергу",
        ["action_type"],
        registry=registry,
    )
    METRICS_AVAILABLE = True
except:
    METRICS_AVAILABLE = False

    class DummyMetric:
        def labels(self, *args, **kwargs):
            return self

        def inc(self, *args, **kwargs):
            pass

        def observe(self, *args, **kwargs):
            pass

    TRACKING_EVENTS_TOTAL = DummyMetric()
    TRACKING_LATENCY = DummyMetric()


class TrackingMiddleware(BaseMiddleware):
    ACTION_CATEGORIES = {
        "onboarding": ["command_start"],
        "navigation": ["page_view", "button_click"],
        "interaction": ["filter_applied", "search_query"],
        "referral": ["referral_click"],
        "error": ["error_occurred"],
    }

    async def __call__(
        self,
        handler: Callable[[Update, Dict[str, Any]], Awaitable[Any]],
        event: Update,
        data: Dict[str, Any],
    ) -> Any:
        start_time = time.time()
        user_id = None
        action_type = None
        context = {}

        try:
            if event.message:
                user_id = event.message.from_user.id
                action_type = self._get_message_action_type(event.message)
                context = self._extract_message_context(event.message)

            elif event.callback_query:
                user_id = event.callback_query.from_user.id
                action_type = "button_click"
                context = self._extract_callback_context(event.callback_query)

            if user_id:
                session_id = await session_manager.get_or_create_session(user_id)

                result = await handler(event, data)

                latency_ms = int((time.time() - start_time) * 1000)

                event_data = {
                    "user_id": user_id,
                    "action_type": action_type,
                    "session_id": session_id,
                    "context": context,
                    "platform": "telegram",
                    "latency_ms": latency_ms,
                }

                success = await event_processor.add_event(event_data)

                if success and METRICS_AVAILABLE:
                    TRACKING_EVENTS_TOTAL.labels(action_type=action_type).inc()
                    TRACKING_LATENCY.labels(action_type=action_type).observe(
                        time.time() - start_time
                    )

                return result

            else:
                return await handler(event, data)

        except Exception as e:
            logger.error(f"❌ Помилка в tracking middleware: {e}", exc_info=True)

            try:
                return await handler(event, data)
            except:
                raise

    def _get_message_action_type(self, message: Message) -> str:
        if message.text:
            if message.text.split()[0].split("@")[0] in {"/start", "/main"}:
                return "command_start"
            elif message.text.startswith("/yield"):
                return "command_yield"
            elif message.text.startswith("/top"):
                return "command_top"
            elif message.text.startswith("/help"):
                return "command_help"
            elif message.text.startswith("/recommendations"):
                return "command_recommendations"
            elif message.text.startswith("/exchanges"):
                return "command_exchanges"
            elif message.text.startswith("/rec"):
                return "command_rec"
            elif message.text.startswith("/"):
                return "command_other"
            else:
                return "text_input"
        return "message_other"

    def _extract_message_context(self, message: Message) -> Dict[str, Any]:
        context = {}

        if message.text:
            if message.text.startswith("/"):
                parts = message.text.split(maxsplit=1)
                context["command"] = parts[0]
                if len(parts) > 1:
                    context["args"] = parts[1]
            else:
                context["text_length"] = len(message.text)

        return context

    def _extract_callback_context(self, callback: CallbackQuery) -> Dict[str, Any]:
        context = {"callback_data": callback.data}

        if callback.data:
            if callback.data.startswith("filter_"):
                context["category"] = "filter"
            elif callback.data.startswith("sort_"):
                context["category"] = "sort"
            elif callback.data.startswith("page_"):
                context["category"] = "pagination"
            elif "referral" in callback.data or "ref_" in callback.data:
                context["category"] = "referral"
            else:
                context["category"] = "navigation"

        return context
