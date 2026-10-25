"""Limitation simple du nombre de requêtes coûteuses par client."""

import time
from collections import defaultdict, deque
from threading import Lock

from app.core.exceptions import RateLimitExceededError


class SlidingWindowRateLimiter:
    """Compte les appels sur une fenêtre glissante, en mémoire (suffisant pour un seul processus)."""

    def __init__(self, max_calls: int, window_seconds: float = 60.0) -> None:
        self.max_calls = max_calls
        self.window_seconds = window_seconds
        self._calls: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def check(self, client_key: str) -> None:
        now = time.monotonic()
        with self._lock:
            calls = self._calls[client_key]
            while calls and now - calls[0] > self.window_seconds:
                calls.popleft()
            if len(calls) >= self.max_calls:
                raise RateLimitExceededError()
            calls.append(now)
