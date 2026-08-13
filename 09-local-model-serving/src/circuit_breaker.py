"""Circuit breaker over the connection to the downstream model server
(Ollama). Three states, same as the standard pattern:

  CLOSED     — normal operation, requests pass through.
  OPEN       — FAILURE_THRESHOLD consecutive failures tripped it; requests
               fast-fail immediately (no hang, no wasted timeout) until
               COOLDOWN_SECONDS elapses.
  HALF_OPEN  — cooldown elapsed; the next single request is allowed through
               as a probe. Success -> CLOSED. Failure -> OPEN again, cooldown
               restarts.

This is a single-process, in-memory breaker — same idea as the resume's
"companion health-check endpoint on each host so the load balancer's
target-health checks could automatically pull an unhealthy instance out of
rotation," scoped down to one process's downstream dependency instead of a
fleet behind a load balancer.
"""

import time
from threading import Lock

from config import FAILURE_THRESHOLD, COOLDOWN_SECONDS

CLOSED, OPEN, HALF_OPEN = "CLOSED", "OPEN", "HALF_OPEN"


class CircuitBreaker:
    def __init__(self, failure_threshold=FAILURE_THRESHOLD, cooldown_seconds=COOLDOWN_SECONDS):
        self.failure_threshold = failure_threshold
        self.cooldown_seconds = cooldown_seconds
        self._lock = Lock()
        self._consecutive_failures = 0
        self._state = CLOSED
        self._opened_at = None

    @property
    def state(self) -> str:
        with self._lock:
            if self._state == OPEN and self._opened_at is not None:
                if time.time() - self._opened_at >= self.cooldown_seconds:
                    self._state = HALF_OPEN
            return self._state

    def allow_request(self) -> bool:
        return self.state in (CLOSED, HALF_OPEN)

    def record_success(self):
        with self._lock:
            self._consecutive_failures = 0
            self._state = CLOSED
            self._opened_at = None

    def record_failure(self):
        with self._lock:
            self._consecutive_failures += 1
            if self._state == HALF_OPEN or self._consecutive_failures >= self.failure_threshold:
                self._state = OPEN
                self._opened_at = time.time()

    def snapshot(self) -> dict:
        return {
            "state": self.state,
            "consecutive_failures": self._consecutive_failures,
        }
