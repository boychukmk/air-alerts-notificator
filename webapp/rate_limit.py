import time


class LoginRateLimiter:
    def __init__(self, max_failures: int = 5, window_seconds: float = 300, lockout_seconds: float = 300) -> None:
        self.max_failures = max_failures
        self.window_seconds = window_seconds
        self.lockout_seconds = lockout_seconds
        self._failures: dict[str, list[float]] = {}
        self._blocked_until: dict[str, float] = {}

    def is_blocked(self, key: str) -> bool:
        until = self._blocked_until.get(key)
        if until is None:
            return False
        if time.monotonic() >= until:
            del self._blocked_until[key]
            return False
        return True

    def record_failure(self, key: str) -> None:
        now = time.monotonic()
        attempts = [t for t in self._failures.get(key, []) if now - t < self.window_seconds]
        attempts.append(now)
        self._failures[key] = attempts
        if len(attempts) >= self.max_failures:
            self._blocked_until[key] = now + self.lockout_seconds

    def reset(self, key: str) -> None:
        self._failures.pop(key, None)
        self._blocked_until.pop(key, None)
