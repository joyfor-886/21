import time
import logging
from typing import Any, Callable, Optional

logger = logging.getLogger('Ssuma.CircuitBreaker')


class CircuitBreakerOpenError(Exception):
    pass


class CircuitBreaker:
    """熔断器模式

    状态机: closed → open → half_open → closed/open

    - closed: 正常状态，请求通过
    - open: 熔断状态，请求直接失败
    - half_open: 半开状态，允许少量请求探测
    """

    def __init__(
        self,
        failure_threshold: int = 3,
        recovery_timeout: float = 60.0,
        half_open_max_calls: int = 1,
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_calls = half_open_max_calls
        self._failure_count = 0
        self._last_failure_time: float = 0.0
        self._state = "closed"
        self._half_open_calls = 0
        self._last_state_change = time.time()

    @property
    def state(self) -> str:
        if self._state == "open":
            if time.time() - self._last_failure_time > self.recovery_timeout:
                self._transition("half_open")
        return self._state

    async def call(self, func: Callable, *args: Any, **kwargs: Any) -> Any:
        current_state = self.state

        if current_state == "open":
            raise CircuitBreakerOpenError(
                f"Circuit breaker is open (failures={self._failure_count}, "
                f"recovery_in={max(0, self.recovery_timeout - (time.time() - self._last_failure_time)):.0f}s)"
            )

        if current_state == "half_open":
            if self._half_open_calls >= self.half_open_max_calls:
                raise CircuitBreakerOpenError("Circuit breaker is half_open, max probe calls reached")
            self._half_open_calls += 1

        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise

    def _on_success(self):
        self._failure_count = 0
        if self._state == "half_open":
            self._transition("closed")

    def _on_failure(self):
        self._failure_count += 1
        self._last_failure_time = time.time()
        if self._state == "half_open":
            self._transition("open")
        elif self._failure_count >= self.failure_threshold:
            self._transition("open")

    def _transition(self, new_state: str):
        old_state = self._state
        self._state = new_state
        self._last_state_change = time.time()
        if new_state == "half_open":
            self._half_open_calls = 0
        logger.info(f"CircuitBreaker: {old_state} → {new_state} (failures={self._failure_count})")

    def reset(self):
        self._failure_count = 0
        self._state = "closed"
        self._half_open_calls = 0
        logger.info("CircuitBreaker: manually reset to closed")

    def stats(self) -> dict:
        return {
            "state": self.state,
            "failure_count": self._failure_count,
            "failure_threshold": self.failure_threshold,
            "recovery_timeout": self.recovery_timeout,
            "last_failure_time": self._last_failure_time,
            "last_state_change": self._last_state_change,
        }
