import os
import tempfile

import pytest

from alertbot import settings_store as store

# must be set before `from webapp.app import app` below, which calls store.init_db() on import
store.DB_PATH = os.path.join(tempfile.mkdtemp(), "settings.db")

from fastapi.testclient import TestClient  # noqa: E402

from alertbot.auth import hash_password  # noqa: E402
from webapp.app import app  # noqa: E402

PHONE = "380990000000"
PASSWORD = "12345678"


def _seed_user():
    pw_hash, salt = hash_password(PASSWORD)
    c = store._conn()
    c.execute(
        "INSERT OR REPLACE INTO users (phone, password_hash, salt, name) VALUES (?, ?, ?, ?)",
        (PHONE, pw_hash, salt, None),
    )
    c.execute(
        "INSERT OR REPLACE INTO regions (key, label, target_keywords, transit_keywords) VALUES (?, ?, ?, ?)",
        ("kyiv", "Київ", "[\"київ\"]", "[]"),
    )
    c.execute(
        "INSERT OR REPLACE INTO threat_types (key, label, enabled, keywords) VALUES (?, ?, ?, ?)",
        ("ballistic", "Балістика", 1, "[\"балістик\"]"),
    )
    c.commit()
    c.close()


@pytest.fixture
def client():
    store.init_db()
    _seed_user()
    return TestClient(app)


def _login(client):
    return client.post("/api/login", json={"phone": PHONE, "password": PASSWORD})


def test_state_requires_auth(client):
    resp = client.get("/api/state")
    assert resp.status_code == 401


def test_login_wrong_password(client):
    resp = client.post("/api/login", json={"phone": PHONE, "password": "wrong"})
    assert resp.status_code == 401


def test_login_malformed_body_is_422_not_500(client):
    resp = client.post("/api/login", json={"phone": PHONE})
    assert resp.status_code == 422


def test_login_success_sets_cookie_and_unlocks_state(client):
    resp = _login(client)
    assert resp.status_code == 200
    assert "session" in resp.cookies

    state = client.get("/api/state")
    assert state.status_code == 200
    assert "kyiv" in state.json()["regions"]


def test_region_toggle_malformed_body_is_422(client):
    _login(client)
    resp = client.post("/api/region", json={"region": "kyiv"})
    assert resp.status_code == 422


def test_region_toggle_assigns_topic(client):
    _login(client)
    resp = client.post("/api/region", json={"region": "kyiv", "enabled": True})
    assert resp.status_code == 200

    state = client.get("/api/state").json()
    assert state["regions"]["kyiv"]["enabled"] is True
    assert state["regions"]["kyiv"]["ntfy_topic"] is not None


def test_threat_keyword_add_and_remove(client):
    _login(client)
    client.post("/api/threat/keyword/add", json={"key": "ballistic", "keyword": "іскандер"})
    state = client.get("/api/state").json()
    assert "іскандер" in state["threat_types"]["ballistic"]["keywords"]

    client.post("/api/threat/keyword/remove", json={"key": "ballistic", "keyword": "іскандер"})
    state = client.get("/api/state").json()
    assert "іскандер" not in state["threat_types"]["ballistic"]["keywords"]


def test_logout_clears_session(client):
    _login(client)
    assert client.get("/api/state").status_code == 200

    client.post("/api/logout")
    assert client.get("/api/state").status_code == 401


def test_channels_add_empty_input_is_rejected(client):
    _login(client)
    resp = client.post("/api/channels/add", json={"input": "  "})
    assert resp.status_code == 400
