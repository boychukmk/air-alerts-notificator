import json
import secrets
import sqlite3
import time
from contextlib import closing
from typing import Any

from alertbot.paths import DATA_DIR

DB_PATH = str(DATA_DIR / "settings.db")


def _conn() -> sqlite3.Connection:
    c = sqlite3.connect(DB_PATH, timeout=5.0)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA journal_mode=WAL")
    c.execute("PRAGMA busy_timeout=5000")
    return c


def init_db() -> None:
    with closing(_conn()) as c:
        c.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                phone TEXT PRIMARY KEY,
                password_hash TEXT NOT NULL,
                salt TEXT NOT NULL,
                name TEXT
            );
            CREATE TABLE IF NOT EXISTS regions (
                key TEXT PRIMARY KEY,
                label TEXT NOT NULL,
                target_keywords TEXT NOT NULL,
                transit_keywords TEXT NOT NULL,
                enabled INTEGER NOT NULL DEFAULT 0,
                ntfy_topic TEXT
            );
            CREATE TABLE IF NOT EXISTS threat_types (
                key TEXT PRIMARY KEY,
                label TEXT NOT NULL,
                enabled INTEGER NOT NULL,
                keywords TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS channels (
                key TEXT PRIMARY KEY,
                label TEXT NOT NULL,
                enabled INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS app_state (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS sessions (
                token TEXT PRIMARY KEY,
                phone TEXT NOT NULL,
                created_ts REAL NOT NULL
            );
            CREATE TABLE IF NOT EXISTS join_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                raw_input TEXT NOT NULL,
                status TEXT NOT NULL,
                result TEXT,
                created_ts REAL NOT NULL
            );
            """
        )
        for stmt in (
            "ALTER TABLE regions ADD COLUMN enabled INTEGER NOT NULL DEFAULT 0",
            "ALTER TABLE regions ADD COLUMN ntfy_topic TEXT",
        ):
            try:
                c.execute(stmt)
            except sqlite3.OperationalError:
                pass

        legacy = c.execute("SELECT value FROM app_state WHERE key='active_region'").fetchone()
        if legacy:
            legacy_topic = c.execute("SELECT value FROM app_state WHERE key='ntfy_topic'").fetchone()
            topic = legacy_topic["value"] if legacy_topic else None
            c.execute(
                "UPDATE regions SET enabled=1, ntfy_topic=COALESCE(ntfy_topic, ?) WHERE key=? AND ntfy_topic IS NULL",
                (topic, legacy["value"]),
            )
            c.execute("DELETE FROM app_state WHERE key='active_region'")

        c.commit()


def get_state() -> dict[str, Any]:
    with closing(_conn()) as c:
        regions = {}
        for row in c.execute("SELECT * FROM regions"):
            regions[row["key"]] = {
                "label": row["label"],
                "target_keywords": json.loads(row["target_keywords"]),
                "transit_keywords": json.loads(row["transit_keywords"]),
                "enabled": bool(row["enabled"]),
                "ntfy_topic": row["ntfy_topic"],
            }

        threat_types = {}
        for row in c.execute("SELECT * FROM threat_types"):
            threat_types[row["key"]] = {
                "label": row["label"],
                "enabled": bool(row["enabled"]),
                "keywords": json.loads(row["keywords"]),
            }

        channels = []
        for row in c.execute("SELECT * FROM channels"):
            channels.append({"key": row["key"], "label": row["label"], "enabled": bool(row["enabled"])})

        ntfy_server_row = c.execute("SELECT value FROM app_state WHERE key='ntfy_server'").fetchone()
        ntfy_server = ntfy_server_row["value"] if ntfy_server_row else "https://ntfy.sh"

        return {
            "regions": regions,
            "threat_types": threat_types,
            "channels": channels,
            "ntfy_server": ntfy_server,
            "ntfy_priority": "urgent",
        }


def set_region_enabled(region_key: str, enabled: bool) -> None:
    if enabled:
        ensure_region_topic(region_key)
    with closing(_conn()) as c:
        c.execute("UPDATE regions SET enabled=? WHERE key=?", (1 if enabled else 0, region_key))
        c.commit()


def ensure_region_topic(region_key: str) -> str:
    """ntfy.sh is public and unauthenticated, so this must be random — never hardcoded."""
    with closing(_conn()) as c:
        row = c.execute("SELECT ntfy_topic FROM regions WHERE key=?", (region_key,)).fetchone()
        if row and row["ntfy_topic"]:
            return row["ntfy_topic"]

        topic = f"alert-{region_key}-{secrets.token_hex(16)}"
        c.execute("UPDATE regions SET ntfy_topic=? WHERE key=?", (topic, region_key))
        c.commit()
        return topic


def set_threat_type_enabled(key: str, enabled: bool) -> None:
    with closing(_conn()) as c:
        c.execute("UPDATE threat_types SET enabled=? WHERE key=?", (1 if enabled else 0, key))
        c.commit()


def add_threat_keyword(key: str, keyword: str) -> None:
    keyword = keyword.strip().lower()
    if not keyword:
        return
    with closing(_conn()) as c:
        row = c.execute("SELECT keywords FROM threat_types WHERE key=?", (key,)).fetchone()
        if not row:
            return
        keywords = json.loads(row["keywords"])
        if keyword not in keywords:
            keywords.append(keyword)
            c.execute("UPDATE threat_types SET keywords=? WHERE key=?", (json.dumps(keywords), key))
            c.commit()


def remove_threat_keyword(key: str, keyword: str) -> None:
    with closing(_conn()) as c:
        row = c.execute("SELECT keywords FROM threat_types WHERE key=?", (key,)).fetchone()
        if not row:
            return
        keywords = [k for k in json.loads(row["keywords"]) if k != keyword]
        c.execute("UPDATE threat_types SET keywords=? WHERE key=?", (json.dumps(keywords), key))
        c.commit()


def set_channel_enabled(key: str, enabled: bool) -> None:
    with closing(_conn()) as c:
        c.execute("UPDATE channels SET enabled=? WHERE key=?", (1 if enabled else 0, key))
        c.commit()


def add_channel(key: str, label: str, enabled: bool = True) -> None:
    with closing(_conn()) as c:
        c.execute(
            "INSERT OR REPLACE INTO channels (key, label, enabled) VALUES (?, ?, ?)",
            (key, label, 1 if enabled else 0),
        )
        c.commit()


def add_join_request(raw_input: str) -> int:
    with closing(_conn()) as c:
        cur = c.execute(
            "INSERT INTO join_requests (raw_input, status, created_ts) VALUES (?, 'pending', ?)",
            (raw_input, time.time()),
        )
        c.commit()
        assert cur.lastrowid is not None
        return cur.lastrowid


def get_pending_join_requests() -> list[dict[str, Any]]:
    with closing(_conn()) as c:
        rows = c.execute("SELECT * FROM join_requests WHERE status='pending' ORDER BY id").fetchall()
        return [dict(r) for r in rows]


def set_join_request_result(request_id: int, status: str, result: str) -> None:
    with closing(_conn()) as c:
        c.execute(
            "UPDATE join_requests SET status=?, result=? WHERE id=?",
            (status, result, request_id),
        )
        c.commit()


def get_join_requests_recent(limit: int = 20) -> list[dict[str, Any]]:
    with closing(_conn()) as c:
        rows = c.execute("SELECT * FROM join_requests ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        return [dict(r) for r in rows]


def get_user(phone: str) -> dict[str, Any] | None:
    with closing(_conn()) as c:
        row = c.execute("SELECT * FROM users WHERE phone=?", (phone,)).fetchone()
        return dict(row) if row else None


SESSION_MAX_AGE_SECONDS = 60 * 60 * 24 * 30


def create_session(token: str, phone: str) -> None:
    with closing(_conn()) as c:
        c.execute("INSERT INTO sessions (token, phone, created_ts) VALUES (?, ?, ?)", (token, phone, time.time()))
        c.commit()


def get_session(token: str) -> dict[str, Any] | None:
    with closing(_conn()) as c:
        row = c.execute("SELECT * FROM sessions WHERE token=?", (token,)).fetchone()
    if not row:
        return None
    if time.time() - row["created_ts"] > SESSION_MAX_AGE_SECONDS:
        delete_session(token)
        return None
    return dict(row)


def delete_session(token: str) -> None:
    with closing(_conn()) as c:
        c.execute("DELETE FROM sessions WHERE token=?", (token,))
        c.commit()


def set_heartbeat() -> None:
    with closing(_conn()) as c:
        c.execute(
            "INSERT OR REPLACE INTO app_state (key, value) VALUES ('monitor_heartbeat_ts', ?)",
            (str(time.time()),),
        )
        c.commit()


def get_heartbeat() -> float | None:
    with closing(_conn()) as c:
        row = c.execute("SELECT value FROM app_state WHERE key='monitor_heartbeat_ts'").fetchone()
    return float(row["value"]) if row else None
