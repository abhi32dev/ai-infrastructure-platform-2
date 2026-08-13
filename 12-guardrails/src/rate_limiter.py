"""Token-bucket rate limiter, per user_id, in-memory. Same primitive a
production API gateway uses; here scoped to gate LLM calls specifically
since those are the expensive/abusable resource.
"""

import time
from threading import Lock


class TokenBucketLimiter:
    def __init__(self, capacity: int, refill_per_second: float):
        self.capacity = capacity
        self.refill_per_second = refill_per_second
        self._buckets: dict[str, tuple[float, float]] = {}  # user_id -> (tokens, last_refill_ts)
        self._lock = Lock()

    def allow(self, user_id: str, cost: float = 1.0) -> bool:
        with self._lock:
            now = time.time()
            tokens, last_refill = self._buckets.get(user_id, (self.capacity, now))

            elapsed = now - last_refill
            tokens = min(self.capacity, tokens + elapsed * self.refill_per_second)

            if tokens >= cost:
                tokens -= cost
                self._buckets[user_id] = (tokens, now)
                return True

            self._buckets[user_id] = (tokens, now)
            return False

    def remaining(self, user_id: str) -> float:
        with self._lock:
            tokens, _ = self._buckets.get(user_id, (self.capacity, time.time()))
            return tokens
