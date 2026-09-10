from alertbot.dedup import InMemoryDedup


def test_first_message_is_not_duplicate():
    dedup = InMemoryDedup(window_seconds=180)
    assert dedup.is_duplicate("Балістика на Київ") is False


def test_exact_repeat_is_duplicate():
    dedup = InMemoryDedup(window_seconds=180)
    dedup.is_duplicate("Балістика на Київ")
    assert dedup.is_duplicate("Балістика на Київ") is True


def test_case_and_whitespace_insensitive():
    dedup = InMemoryDedup(window_seconds=180)
    dedup.is_duplicate("Балістика   на Київ")
    assert dedup.is_duplicate("балістика на київ") is True


def test_different_text_is_not_duplicate():
    dedup = InMemoryDedup(window_seconds=180)
    dedup.is_duplicate("Балістика на Київ")
    assert dedup.is_duplicate("Ракета на Одесу") is False


def test_evicts_stale_entries(monkeypatch):
    import time as time_module

    dedup = InMemoryDedup(window_seconds=10)
    fake_now = [1000.0]
    monkeypatch.setattr(time_module, "monotonic", lambda: fake_now[0])

    dedup.is_duplicate("Балістика на Київ")
    fake_now[0] += 20
    assert dedup.is_duplicate("Балістика на Київ") is False
