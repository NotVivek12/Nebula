import time
from typing import Any, Callable


class CircuitBreakerOpenException(Exception):
    """Exception raised when a circuit breaker is currently open."""

    pass


class CircuitBreaker:
    """Circuit breaker wrapper protecting integrations and LLM connectors from cascading failure."""

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_seconds: int = 30,
    ) -> None:
        self.failure_threshold = failure_threshold
        self.recovery_seconds = recovery_seconds
        self.state = "CLOSED"  # CLOSED, OPEN, HALF-OPEN
        self.consecutive_failures = 0
        self.last_state_change = time.time()

    def record_success(self) -> None:
        self.consecutive_failures = 0
        self.state = "CLOSED"

    def record_failure(self) -> None:
        self.consecutive_failures += 1
        if self.consecutive_failures >= self.failure_threshold:
            self.state = "OPEN"
            self.last_state_change = time.time()

    def check_state(self) -> None:
        if self.state == "OPEN":
            # Check if recovery window has passed
            if time.time() - self.last_state_change > self.recovery_seconds:
                self.state = "HALF-OPEN"
                self.last_state_change = time.time()
            else:
                raise CircuitBreakerOpenException(
                    "Circuit is open. Dynamic downstreams are temporarily blocked."
                )

    async def call(self, func: Callable, *args: Any, **kwargs: Any) -> Any:
        self.check_state()
        try:
            res = await func(*args, **kwargs)
            self.record_success()
            return res
        except Exception:
            self.record_failure()
            raise
