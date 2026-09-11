import time

import pytest

from alertbot import settings_store as store


@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "DB_PATH", str(tmp_path / "settings.db"))
    store.init_db()
    c = store._conn()
    c.execute(
        "INSERT INTO regions (key, label, target_keywords, transit_keywords) VALUES (?, ?, ?, ?)",
        ("kyiv", "Київ", "[\"київ\"]", "[]"),
    )
    c.execute(
        "INSERT INTO threat_types (key, label, enabled, keywords) VALUES (?, ?, ?, ?)",
        ("ballistic", "Балістика", 1, "[\"балістик\"]"),
    )
    c.commit()
    c.close()


def test_region_starts_disabled_without_topic():
    state = store.get_state()
    assert state["regions"]["kyiv"]["enabled"] is False
    assert state["regions"]["kyiv"]["ntfy_topic"] is None


def test_enabling_region_assigns_topic():
    store.set_region_enabled("kyiv", True)
    state = store.get_state()
    assert state["regions"]["kyiv"]["enabled"] is True
    assert state["regions"]["kyiv"]["ntfy_topic"].startswith("alert-kyiv-")


def test_topic_is_stable_across_toggles():
    store.set_region_enabled("kyiv", True)
    topic1 = store.get_state()["regions"]["kyiv"]["ntfy_topic"]
    store.set_region_enabled("kyiv", False)
    store.set_region_enabled("kyiv", True)
    topic2 = store.get_state()["regions"]["kyiv"]["ntfy_topic"]
    assert topic1 == topic2


def test_add_and_remove_threat_keyword():
    store.add_threat_keyword("ballistic", "іскандер")
    assert "іскандер" in store.get_state()["threat_types"]["ballistic"]["keywords"]

    store.remove_threat_keyword("ballistic", "іскандер")
    assert "іскандер" not in store.get_state()["threat_types"]["ballistic"]["keywords"]


def test_add_threat_keyword_is_idempotent():
    store.add_threat_keyword("ballistic", "балістик")
    keywords = store.get_state()["threat_types"]["ballistic"]["keywords"]
    assert keywords.count("балістик") == 1


def test_add_channel_and_toggle():
    store.add_channel("some_channel", "Some Channel")
    state = store.get_state()
    assert {"key": "some_channel", "label": "Some Channel", "enabled": True} in state["channels"]

    store.set_channel_enabled("some_channel", False)
    state = store.get_state()
    assert [c for c in state["channels"] if c["key"] == "some_channel"][0]["enabled"] is False


def test_join_request_lifecycle():
    request_id = store.add_join_request("@some_channel")
    pending = store.get_pending_join_requests()
    assert any(r["id"] == request_id for r in pending)

    store.set_join_request_result(request_id, "done", "joined: Some Channel")
    pending_after = store.get_pending_join_requests()
    assert not any(r["id"] == request_id for r in pending_after)

    recent = store.get_join_requests_recent(10)
    assert recent[0]["id"] == request_id
    assert recent[0]["status"] == "done"


def test_session_created_and_fetched():
    store.create_session("tok123", "380990000000")
    session = store.get_session("tok123")
    assert session["phone"] == "380990000000"


def test_session_expires_after_max_age(monkeypatch):
    store.create_session("tok123", "380990000000")

    real_time = time.time
    monkeypatch.setattr(time, "time", lambda: real_time() + store.SESSION_MAX_AGE_SECONDS + 10)
    assert store.get_session("tok123") is None

    monkeypatch.undo()
    c = store._conn()
    row = c.execute("SELECT * FROM sessions WHERE token=?", ("tok123",)).fetchone()
    c.close()
    assert row is None


def test_session_deleted_on_logout():
    store.create_session("tok123", "380990000000")
    store.delete_session("tok123")
    assert store.get_session("tok123") is None


def test_get_user_missing_returns_none():
    assert store.get_user("0000000000") is None


def test_heartbeat_starts_unset():
    assert store.get_heartbeat() is None


def test_heartbeat_records_current_time(monkeypatch):
    monkeypatch.setattr(time, "time", lambda: 12345.0)
    store.set_heartbeat()
    assert store.get_heartbeat() == 12345.0
