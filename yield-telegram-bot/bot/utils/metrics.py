"""
Prometheus метрики для моніторингу продуктивності бота.
"""

from typing import Optional
import time
from contextlib import asynccontextmanager

try:
    from prometheus_client import (
        Counter, Histogram, Gauge, Summary,
        generate_latest, CONTENT_TYPE_LATEST,
        CollectorRegistry, start_http_server
    )
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
    # Stub класи для випадків коли prometheus не встановлений
    class Counter:
        def __init__(self, *args, **kwargs): pass
        def inc(self, *args, **kwargs): pass
        def labels(self, *args, **kwargs): return self

    class Histogram:
        def __init__(self, *args, **kwargs): pass
        def observe(self, *args, **kwargs): pass
        def labels(self, *args, **kwargs): return self

    class Gauge:
        def __init__(self, *args, **kwargs): pass
        def set(self, *args, **kwargs): pass
        def inc(self, *args, **kwargs): pass
        def dec(self, *args, **kwargs): pass
        def labels(self, *args, **kwargs): return self

    class Summary:
        def __init__(self, *args, **kwargs): pass
        def observe(self, *args, **kwargs): pass
        def labels(self, *args, **kwargs): return self

    def generate_latest(*args, **kwargs): return b""
    CONTENT_TYPE_LATEST = "text/plain; version=0.0.4; charset=utf-8"


# Створюємо registry для метрик
registry = CollectorRegistry()

# Метрики запитів
REQUEST_DURATION = Histogram(
    'telegram_bot_request_duration_seconds',
    'Час обробки запитів',
    ['method', 'endpoint', 'status'],
    registry=registry
)

REQUEST_TOTAL = Counter(
    'telegram_bot_requests_total',
    'Загальна кількість запитів',
    ['method', 'endpoint', 'status'],
    registry=registry
)

BOT_UPDATES_TOTAL = Counter(
    'telegram_bot_updates_total',
    'Загальна кількість оновлень бота',
    ['update_type'],
    registry=registry
)

BOT_ERRORS_TOTAL = Counter(
    'telegram_bot_errors_total',
    'Загальна кількість помилок бота',
    ['error_type'],
    registry=registry
)

BOT_API_REQUESTS_TOTAL = Counter(
    'telegram_bot_api_requests_total',
    'Загальна кількість API запитів бота',
    ['endpoint', 'method'],
    registry=registry
)

BOT_HANDLER_DURATION_SECONDS = Histogram(
    'telegram_bot_handler_duration_seconds',
    'Час виконання хендлерів',
    ['handler_name'],
    registry=registry
)

# Метрики розсилок
BROADCAST_MESSAGES_TOTAL = Counter(
    'telegram_broadcast_messages_sent_total',
    'Кількість успішно надісланих повідомлень розсилки',
    registry=registry,
)

BROADCAST_FAILURES_TOTAL = Counter(
    'telegram_broadcast_messages_failed_total',
    'Кількість невдалих надсилань розсилки',
    registry=registry,
)

BROADCAST_QUEUE_DEPTH = Gauge(
    'telegram_broadcast_queue_depth',
    'Поточний розмір черги розсилок',
    registry=registry,
)

BROADCAST_IN_PROGRESS = Gauge(
    'telegram_broadcast_in_progress',
    'Кількість розсилок у стані обробки',
    registry=registry,
)

# Метрики кешу
CACHE_HITS = Counter(
    'telegram_bot_cache_hits_total',
    'Кількість попадань в кеш',
    ['cache_type'],
    registry=registry
)

CACHE_MISSES = Counter(
    'telegram_bot_cache_misses_total',
    'Кількість промахів кешу',
    ['cache_type'],
    registry=registry
)

CACHE_HIT_RATIO = Gauge(
    'telegram_bot_cache_hit_ratio',
    'Співвідношення попадань в кеш',
    ['cache_type'],
    registry=registry
)

CACHE_SIZE = Gauge(
    'telegram_bot_cache_size',
    'Розмір кешу',
    ['cache_type'],
    registry=registry
)

# Метрики Circuit Breaker
CIRCUIT_BREAKER_STATE = Gauge(
    'telegram_bot_circuit_breaker_state',
    'Стан circuit breaker (0=closed, 1=open, 2=half_open)',
    ['breaker_name'],
    registry=registry
)

CIRCUIT_BREAKER_FAILURES = Counter(
    'telegram_bot_circuit_breaker_failures_total',
    'Кількість помилок circuit breaker',
    ['breaker_name'],
    registry=registry
)

# Метрики API клієнта
API_REQUEST_DURATION = Histogram(
    'telegram_bot_api_request_duration_seconds',
    'Час API запитів',
    ['endpoint', 'method'],
    registry=registry
)

API_REQUEST_TOTAL = Counter(
    'telegram_bot_api_client_requests_total',
    'Загальна кількість API запитів клієнта',
    ['endpoint', 'method', 'status'],
    registry=registry
)

API_CACHE_HITS = Counter(
    'telegram_bot_api_cache_hits_total',
    'Попадання в API кеш',
    ['endpoint'],
    registry=registry
)

# Метрики користувачів
ACTIVE_USERS = Gauge(
    'telegram_bot_active_users',
    'Кількість активних користувачів',
    registry=registry
)

CONCURRENT_REQUESTS = Gauge(
    'telegram_bot_concurrent_requests',
    'Кількість одночасних запитів',
    registry=registry
)

# Метрики throttling
BOT_THROTTLED_TOTAL = Counter(
    'telegram_bot_throttled_total',
    'Загальна кількість throttling подій',
    ['user_id'],
    registry=registry
)

# Метрики трекінгу
TRACKING_EVENTS_TOTAL = Counter(
    'telegram_bot_tracking_events_total',
    'Загальна кількість трекінгових подій',
    ['action_type'],
    registry=registry
)

TRACKING_QUEUE_SIZE = Gauge(
    'telegram_bot_tracking_queue_size',
    'Розмір черги трекінгових подій',
    registry=registry
)

TRACKING_BATCH_WRITES = Counter(
    'telegram_bot_tracking_batch_writes_total',
    'Кількість батч-записів у БД',
    registry=registry
)

TRACKING_ERRORS = Counter(
    'telegram_bot_tracking_errors_total',
    'Кількість помилок трекінгу',
    ['error_type'],
    registry=registry
)

# Метрики помилок (використовується BOT_ERRORS_TOTAL)

# Метрики продуктивності
MEMORY_USAGE = Gauge(
    'telegram_bot_memory_usage_bytes',
    'Використання пам\'яті',
    registry=registry
)

CPU_USAGE = Gauge(
    'telegram_bot_cpu_usage_percent',
    'Використання CPU',
    ['core'],
    registry=registry
)


class MetricsCollector:
    """Збирач метрик для моніторингу."""

    def __init__(self):
        self._started = False

    def start_server(self, port: int = 8001):
        """Запустити HTTP сервер для експорту метрик."""
        if not PROMETHEUS_AVAILABLE:
            print("⚠️  Prometheus не встановлений, метрики недоступні")
            return

        if not self._started:
            try:
                start_http_server(port, registry=registry)
                print(f"📊 Prometheus метрики доступні на http://localhost:{port}/metrics")
                self._started = True
            except Exception as e:
                print(f"❌ Помилка запуску Prometheus сервера: {e}")

    def get_metrics_text(self) -> str:
        """Отримати метрики у текстовому форматі."""
        if not PROMETHEUS_AVAILABLE:
            return "# Prometheus не встановлений"

        return generate_latest(registry).decode('utf-8')

    @asynccontextmanager
    async def measure_request(self, method: str, endpoint: str):
        """Контекстний менеджер для вимірювання часу запиту."""
        start_time = time.time()
        status = "success"

        try:
            yield
        except Exception as e:
            status = "error"
            BOT_ERRORS_TOTAL.labels(error_type=type(e).__name__).inc()
            raise
        finally:
            duration = time.time() - start_time
            REQUEST_DURATION.labels(method=method, endpoint=endpoint, status=status).observe(duration)
            REQUEST_TOTAL.labels(method=method, endpoint=endpoint, status=status).inc()

    @asynccontextmanager
    async def measure_api_request(self, endpoint: str, method: str = "GET"):
        """Контекстний менеджер для вимірювання API запитів."""
        start_time = time.time()
        status = "success"

        try:
            yield
        except Exception as e:
            status = "error"
            BOT_ERRORS_TOTAL.labels(error_type=type(e).__name__).inc()
            raise
        finally:
            duration = time.time() - start_time
            API_REQUEST_DURATION.labels(endpoint=endpoint, method=method).observe(duration)
            API_REQUEST_TOTAL.labels(endpoint=endpoint, method=method, status=status).inc()

    def update_cache_metrics(self, cache_type: str, hits: int, misses: int, size: Optional[int] = None):
        """Оновити метрики кешу."""
        CACHE_HITS.labels(cache_type=cache_type).inc(hits)
        CACHE_MISSES.labels(cache_type=cache_type).inc(misses)

        total = hits + misses
        if total > 0:
            hit_ratio = hits / total
            CACHE_HIT_RATIO.labels(cache_type=cache_type).set(hit_ratio)

        if size is not None:
            CACHE_SIZE.labels(cache_type=cache_type).set(size)

    def update_circuit_breaker_metrics(self, breaker_name: str, state: str, failures: int):
        """Оновити метрики circuit breaker."""
        # Перетворюємо стан в число
        state_value = {"closed": 0, "open": 1, "half_open": 2}.get(state, 0)
        CIRCUIT_BREAKER_STATE.labels(breaker_name=breaker_name).set(state_value)
        CIRCUIT_BREAKER_FAILURES.labels(breaker_name=breaker_name).inc(failures)

    def update_user_metrics(self, active_users: int, concurrent_requests: int):
        """Оновити метрики користувачів."""
        ACTIVE_USERS.set(active_users)
        CONCURRENT_REQUESTS.set(concurrent_requests)

    def update_api_cache_hit(self, endpoint: str):
        """Зафіксувати попадання в API кеш."""
        API_CACHE_HITS.labels(endpoint=endpoint).inc()


# Глобальний збирач метрик
metrics_collector = MetricsCollector()


# Допоміжні функції для легкого використання
async def measure_operation_time(operation_name: str, coro):
    """
    Виміряти час виконання асинхронної операції.

    Args:
        operation_name: Назва операції для логування
        coro: Корутина для виконання

    Returns:
        Результат виконання корутини
    """
    start_time = time.time()
    try:
        result = await coro
        duration = time.time() - start_time
        print(f"⏱️  Операція '{operation_name}' виконана за {duration:.3f}с")
        return result
    except Exception as e:
        duration = time.time() - start_time
        print(f"❌ Операція '{operation_name}' завершилася помилкою за {duration:.3f}с: {e}")
        raise


def track_cache_operation(cache_type: str, operation: str):
    """
    Декоратор для відстеження операцій кешу.

    Args:
        cache_type: Тип кешу (redis, api, memory)
        operation: Тип операції (hit, miss, set, delete)
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            try:
                result = await func(*args, **kwargs)

                if operation == "hit":
                    CACHE_HITS.labels(cache_type=cache_type).inc()
                elif operation == "miss":
                    CACHE_MISSES.labels(cache_type=cache_type).inc()

                return result
            except Exception as e:
                BOT_ERRORS_TOTAL.labels(error_type=type(e).__name__).inc()
                raise

        return wrapper
    return decorator