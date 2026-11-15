import asyncio
import time
from enum import Enum
from typing import Any, Callable, Dict, Optional
from contextlib import asynccontextmanager

from bot.utils.logger import logger
from bot.utils.metrics import CIRCUIT_BREAKER_STATE, CIRCUIT_BREAKER_FAILURES


class CircuitBreakerState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    def __init__(
        self,
        failure_threshold: int = 5,
        timeout: int = 60,
        expected_exception: Exception = Exception,
        name: str = "default",
    ):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.expected_exception = expected_exception
        self.name = name

        self.state = CircuitBreakerState.CLOSED
        self.failures = 0
        self.last_failure_time = 0
        self.next_attempt_time = 0

        self.total_requests = 0
        self.total_failures = 0
        self.total_successes = 0
        self.consecutive_successes = 0

        self._lock = asyncio.Lock()

        CIRCUIT_BREAKER_STATE.labels(breaker_name=self.name).set(0)  # CLOSED

    async def call(self, func: Callable, *args, **kwargs) -> Any:
        async with self._lock:
            self.total_requests += 1

            if self.state == CircuitBreakerState.OPEN:
                if time.time() < self.next_attempt_time:
                    raise CircuitBreakerOpenException(
                        f"Circuit breaker '{self.name}' is OPEN. "
                        f"Next attempt in {self.next_attempt_time - time.time():.1f}s"
                    )

                self.state = CircuitBreakerState.HALF_OPEN
                logger.info(f"🔄 Circuit breaker '{self.name}' -> HALF_OPEN (testing recovery)")

            try:
                result = await func(*args, **kwargs)

                await self._on_success()
                return result

            except self.expected_exception as e:
                await self._on_failure()
                raise e

    async def _on_success(self):
        self.total_successes += 1

        if self.state == CircuitBreakerState.HALF_OPEN:
            self.consecutive_successes += 1
            if self.consecutive_successes >= 3:
                self.state = CircuitBreakerState.CLOSED
                self.failures = 0
                self.consecutive_successes = 0
                CIRCUIT_BREAKER_STATE.labels(breaker_name=self.name).set(0)  # CLOSED
                logger.info(f"✅ Circuit breaker '{self.name}' -> CLOSED (recovered)")
        else:
            self.consecutive_successes = 0

    async def _on_failure(self):
        self.total_failures += 1
        self.failures += 1
        self.last_failure_time = time.time()

        CIRCUIT_BREAKER_FAILURES.labels(breaker_name=self.name).inc()

        if self.state == CircuitBreakerState.HALF_OPEN:
            self.state = CircuitBreakerState.OPEN
            self.next_attempt_time = time.time() + self.timeout
            self.consecutive_successes = 0
            CIRCUIT_BREAKER_STATE.labels(breaker_name=self.name).set(1)  # OPEN
            logger.warning(f"❌ Circuit breaker '{self.name}' -> OPEN (test failed)")
        elif self.failures >= self.failure_threshold:
            self.state = CircuitBreakerState.OPEN
            self.next_attempt_time = time.time() + self.timeout
            CIRCUIT_BREAKER_STATE.labels(breaker_name=self.name).set(1)  # OPEN
            logger.error(
                f"🚨 Circuit breaker '{self.name}' -> OPEN "
                f"({self.failures} failures, threshold: {self.failure_threshold})"
            )

    def get_stats(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "state": self.state.value,
            "failures": self.failures,
            "total_requests": self.total_requests,
            "total_successes": self.total_successes,
            "total_failures": self.total_failures,
            "failure_rate": (self.total_failures / self.total_requests * 100)
            if self.total_requests > 0
            else 0,
            "time_to_next_attempt": max(0, self.next_attempt_time - time.time())
            if self.state == CircuitBreakerState.OPEN
            else 0,
        }

    @asynccontextmanager
    async def protect(self):
        if self.state == CircuitBreakerState.OPEN:
            if time.time() < self.next_attempt_time:
                raise CircuitBreakerOpenException(f"Circuit breaker '{self.name}' is OPEN")
            self.state = CircuitBreakerState.HALF_OPEN

        try:
            yield
            await self._on_success()
        except self.expected_exception as e:
            await self._on_failure()
            raise e


class CircuitBreakerOpenException(Exception):
    pass


api_circuit_breaker = CircuitBreaker(
    name="api_service", failure_threshold=3, timeout=30, expected_exception=Exception
)

redis_circuit_breaker = CircuitBreaker(
    name="redis_cache", failure_threshold=5, timeout=60, expected_exception=Exception
)
