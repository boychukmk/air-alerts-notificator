import time

from webapp.rate_limit import LoginRateLimiter


def test_not_blocked_initially():
    limiter = LoginRateLimiter()
    assert limiter.is_blocked("1.2.3.4") is False


def test_blocked_after_max_failures():
    limiter = LoginRateLimiter(max_failures=3, window_seconds=60, lockout_seconds=60)
    for _ in range(3):
        limiter.record_failure("1.2.3.4")
    assert limiter.is_blocked("1.2.3.4") is True


def test_not_blocked_below_max_failures():
    limiter = LoginRateLimiter(max_failures=3, window_seconds=60, lockout_seconds=60)
    limiter.record_failure("1.2.3.4")
    limiter.record_failure("1.2.3.4")
    assert limiter.is_blocked("1.2.3.4") is False


def test_reset_clears_block(monkeypatch):
    limiter = LoginRateLimiter(max_failures=2, window_seconds=60, lockout_seconds=60)
    limiter.record_failure("1.2.3.4")
    limiter.record_failure("1.2.3.4")
    assert limiter.is_blocked("1.2.3.4") is True

    limiter.reset("1.2.3.4")
    assert limiter.is_blocked("1.2.3.4") is False


def test_lockout_expires(monkeypatch):
    limiter = LoginRateLimiter(max_failures=2, window_seconds=60, lockout_seconds=60)
    fake_now = [1000.0]
    monkeypatch.setattr(time, "monotonic", lambda: fake_now[0])

    limiter.record_failure("1.2.3.4")
    limiter.record_failure("1.2.3.4")
    assert limiter.is_blocked("1.2.3.4") is True

    fake_now[0] += 61
    assert limiter.is_blocked("1.2.3.4") is False


def test_failures_outside_window_do_not_accumulate():
    limiter = LoginRateLimiter(max_failures=3, window_seconds=10, lockout_seconds=60)
    fake_now = [1000.0]
    real_monotonic = time.monotonic
    time.monotonic = lambda: fake_now[0]
    try:
        limiter.record_failure("1.2.3.4")
        limiter.record_failure("1.2.3.4")
        fake_now[0] += 20  # past the window — old failures expire
        limiter.record_failure("1.2.3.4")
        assert limiter.is_blocked("1.2.3.4") is False
    finally:
        time.monotonic = real_monotonic


def test_different_keys_are_independent():
    limiter = LoginRateLimiter(max_failures=2, window_seconds=60, lockout_seconds=60)
    limiter.record_failure("1.2.3.4")
    limiter.record_failure("1.2.3.4")
    assert limiter.is_blocked("1.2.3.4") is True
    assert limiter.is_blocked("5.6.7.8") is False
