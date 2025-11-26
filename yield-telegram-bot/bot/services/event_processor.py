"""
Обробник подій з використанням Redis Streams для батч-запису.
"""
import asyncio
import json
from typing import Dict, Any, List, Optional
from datetime import datetime, UTC
import redis.asyncio as redis
from bot.config import settings
from bot.utils.logger import logger
from bot.db.database import get_database_session
from bot.db.models import UserAction


class EventProcessor:
    """Асинхронний обробник подій з батч-записом."""

    STREAM_KEY = "tracking:events"
    CONSUMER_GROUP = "tracking_workers"
    CONSUMER_NAME = "worker_1"
    BATCH_SIZE = 100  # Записувати по 100 подій
    BATCH_INTERVAL = 5  # Або кожні 5 секунд

    def __init__(self):
        self.redis: Optional[redis.Redis] = None
        self.running = False
        self.task: Optional[asyncio.Task] = None

    async def initialize(self):
        """Ініціалізація Redis та створення consumer group."""
        try:
            self.redis = redis.from_url(settings.REDIS_URL, decode_responses=False)

            # Перевірка з'єднання
            await self.redis.ping()

            # Створення consumer group
            try:
                await self.redis.xgroup_create(
                    self.STREAM_KEY,
                    self.CONSUMER_GROUP,
                    id='0',
                    mkstream=True
                )
                logger.info(f"✅ Consumer group створено: {self.CONSUMER_GROUP}")
            except redis.ResponseError as e:
                if "BUSYGROUP" not in str(e):
                    logger.error(f"❌ Помилка створення consumer group: {e}")
                else:
                    logger.info(f"ℹ️ Consumer group вже існує: {self.CONSUMER_GROUP}")

        except Exception as e:
            logger.error(f"❌ Помилка ініціалізації EventProcessor: {e}")
            raise

    async def add_event(self, event_data: Dict[str, Any]) -> bool:
        """
        Додати подію до черги.

        Args:
            event_data: Дані події

        Returns:
            True якщо успішно додано
        """
        try:
            # Серіалізувати context
            if "context" in event_data and event_data["context"]:
                event_data["context"] = json.dumps(event_data["context"])

            # Додати timestamp якщо відсутній
            if "timestamp" not in event_data:
                event_data["timestamp"] = datetime.now(UTC).isoformat()

            # Конвертувати всі значення в строки для Redis
            redis_data = {
                str(key): str(value) if value is not None else ""
                for key, value in event_data.items()
            }

            # Додати до Redis Stream
            await self.redis.xadd(self.STREAM_KEY, redis_data, maxlen=10000)
            return True

        except Exception as e:
            logger.error(f"❌ Помилка додавання події: {e}")
            return False

    async def start_processing(self):
        """Запустити обробку подій у фоні."""
        if self.running:
            logger.warning("⚠️ Event processor вже запущений")
            return

        self.running = True
        self.task = asyncio.create_task(self._process_loop())
        logger.info("🚀 Event processor запущений")

    async def stop_processing(self):
        """Зупинити обробку."""
        self.running = False
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        logger.info("🛑 Event processor зупинений")

    async def _process_loop(self):
        """Основний цикл обробки подій."""
        last_batch_time = datetime.now(UTC)

        while self.running:
            try:
                # Читати події з Redis Stream
                messages = await self.redis.xreadgroup(
                    self.CONSUMER_GROUP,
                    self.CONSUMER_NAME,
                    {self.STREAM_KEY: '>'},
                    count=self.BATCH_SIZE,
                    block=1000  # Блокувати на 1 секунду
                )

                if messages:
                    await self._process_batch(messages)
                    last_batch_time = datetime.now(UTC)

                # Перевірити інтервал батчу
                time_since_batch = (datetime.now(UTC) - last_batch_time).total_seconds()
                if time_since_batch >= self.BATCH_INTERVAL:
                    # Примусово обробити маленький батч
                    messages = await self.redis.xreadgroup(
                        self.CONSUMER_GROUP,
                        self.CONSUMER_NAME,
                        {self.STREAM_KEY: '>'},
                        count=10,
                        block=0
                    )
                    if messages:
                        await self._process_batch(messages)
                    last_batch_time = datetime.now(UTC)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"❌ Помилка в циклі обробки: {e}", exc_info=True)
                await asyncio.sleep(1)

    async def _process_batch(self, messages):
        """Обробити батч повідомлень."""
        events_to_insert = []
        message_ids = []

        for stream_name, stream_messages in messages:
            for message_id, message_data in stream_messages:
                try:
                    # Десеріалізувати context
                    context_bytes = message_data.get(b'context')
                    context = None
                    if context_bytes and context_bytes != b'':
                        try:
                            context = json.loads(context_bytes.decode())
                        except:
                            context = None

                    # Конвертувати в словник
                    event = {
                        key.decode() if isinstance(key, bytes) else key:
                        value.decode() if isinstance(value, bytes) else value
                        for key, value in message_data.items()
                    }

                    # Додати десеріалізований context
                    if context:
                        event['context'] = context

                    events_to_insert.append(event)
                    message_ids.append(message_id)

                except Exception as e:
                    logger.error(f"❌ Помилка обробки повідомлення: {e}")

        # Батч-запис у БД
        if events_to_insert:
            success = await self._bulk_insert(events_to_insert)

            if success:
                # Підтвердити обробку повідомлень
                for msg_id in message_ids:
                    await self.redis.xack(self.STREAM_KEY, self.CONSUMER_GROUP, msg_id)
                    await self.redis.xdel(self.STREAM_KEY, msg_id)

                logger.info(f"✅ Оброблено {len(events_to_insert)} подій")

    async def _bulk_insert(self, events: List[Dict[str, Any]]) -> bool:
        """
        Батч-запис подій у PostgreSQL.

        Args:
            events: Список подій

        Returns:
            True якщо успішно
        """
        try:
            async with get_database_session() as session:
                user_actions = []

                for event in events:
                    try:
                        # Конвертувати timestamp
                        timestamp_str = event.get("timestamp")
                        timestamp = datetime.fromisoformat(timestamp_str) if timestamp_str else datetime.now(UTC)

                        # Конвертувати latency_ms
                        latency_ms = None
                        if event.get("latency_ms"):
                            try:
                                latency_ms = int(event["latency_ms"])
                            except:
                                pass

                        # Конвертувати context назад в JSON string для зберігання
                        context_str = None
                        if event.get("context"):
                            context_str = json.dumps(event["context"]) if isinstance(event["context"], dict) else event["context"]

                        user_action = UserAction(
                            user_id=int(event.get("user_id")),
                            action_type=event.get("action_type"),
                            timestamp=timestamp,
                            session_id=event.get("session_id"),
                            context=context_str,
                            ref_id=event.get("ref_id"),
                            platform=event.get("platform", "telegram"),
                            latency_ms=latency_ms
                        )
                        user_actions.append(user_action)

                    except Exception as e:
                        logger.error(f"❌ Помилка обробки події для БД: {e}")
                        continue

                if user_actions:
                    session.add_all(user_actions)
                    await session.commit()
                    return True
                else:
                    return False

        except Exception as e:
            logger.error(f"❌ Помилка батч-запису: {e}", exc_info=True)
            return False

    async def close(self):
        """Закрити з'єднання."""
        await self.stop_processing()
        if self.redis:
            await self.redis.close()


# Глобальний екземпляр event processor
event_processor = EventProcessor()

