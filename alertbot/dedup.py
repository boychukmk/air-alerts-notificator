import hashlib
import time


class InMemoryDedup:
    """Fast dedup, no DB round-trip on the hot path — pure in-process dict."""

    def __init__(self, window_seconds: int) -> None:
        self.window_seconds = window_seconds
        self._seen: dict[str, float] = {}

    @staticmethod
    def _fingerprint(text: str) -> str:
        normalized = " ".join(text.lower().split())
        return hashlib.sha1(normalized.encode("utf-8")).hexdigest()

    def is_duplicate(self, text: str) -> bool:
        now = time.monotonic()
        self._evict(now)

        fp = self._fingerprint(text)
        if fp in self._seen:
            return True

        self._seen[fp] = now
        return False

    def _evict(self, now: float) -> None:
        cutoff = now - self.window_seconds
        stale = [fp for fp, ts in self._seen.items() if ts < cutoff]
        for fp in stale:
            del self._seen[fp]
