import time


class ChannelWindowBuffer:
    """Keeps recent messages per channel so short bursts ("Балістика" / "Курс на Київ")
    posted as separate messages can be evaluated together."""

    def __init__(self, window_seconds: int, max_messages: int):
        self.window_seconds = window_seconds
        self.max_messages = max_messages
        self._buffers: dict[str, list[tuple[float, str]]] = {}

    def add_and_get_window(self, channel_key: str, text: str) -> list[str]:
        now = time.monotonic()
        buf = self._buffers.setdefault(channel_key, [])
        buf.append((now, text))

        cutoff = now - self.window_seconds
        buf[:] = [(ts, t) for ts, t in buf if ts >= cutoff][-self.max_messages:]

        return [t for _, t in buf]
