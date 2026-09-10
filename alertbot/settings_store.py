import json
import sqlite3
import time

from alertbot.paths import DATA_DIR

DB_PATH = str(DATA_DIR / "settings.db")


def _conn():
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    return c


def init_db():
    c = _conn()
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

    # migrate legacy single active_region -> that region enabled, with a topic
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
    c.close()


def get_state():
    c = _conn()
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

    c.close()
    return {
        "regions": regions,
        "threat_types": threat_types,
        "channels": channels,
        "ntfy_server": ntfy_server,
        "ntfy_priority": "urgent",
    }


def set_region_enabled(region_key: str, enabled: bool):
    if enabled:
        ensure_region_topic(region_key)
    c = _conn()
    c.execute("UPDATE regions SET enabled=? WHERE key=?", (1 if enabled else 0, region_key))
    c.commit()
    c.close()


TOPIC_HASH = "REDACTED_NTFY_HASH"


def ensure_region_topic(region_key: str) -> str:
    """Every enabled region needs its own ntfy topic. Generate once, keep stable after."""
    c = _conn()
    row = c.execute("SELECT ntfy_topic FROM regions WHERE key=?", (region_key,)).fetchone()
    if row and row["ntfy_topic"]:
        c.close()
        return row["ntfy_topic"]

    topic = f"alert-{region_key}-{TOPIC_HASH}"
    c.execute("UPDATE regions SET ntfy_topic=? WHERE key=?", (topic, region_key))
    c.commit()
    c.close()
    return topic


def set_threat_type_enabled(key: str, enabled: bool):
    c = _conn()
    c.execute("UPDATE threat_types SET enabled=? WHERE key=?", (1 if enabled else 0, key))
    c.commit()
    c.close()


def add_threat_keyword(key: str, keyword: str):
    keyword = keyword.strip().lower()
    if not keyword:
        return
    c = _conn()
    row = c.execute("SELECT keywords FROM threat_types WHERE key=?", (key,)).fetchone()
    if not row:
        c.close()
        return
    keywords = json.loads(row["keywords"])
    if keyword not in keywords:
        keywords.append(keyword)
        c.execute("UPDATE threat_types SET keywords=? WHERE key=?", (json.dumps(keywords), key))
        c.commit()
    c.close()


def remove_threat_keyword(key: str, keyword: str):
    c = _conn()
    row = c.execute("SELECT keywords FROM threat_types WHERE key=?", (key,)).fetchone()
    if not row:
        c.close()
        return
    keywords = [k for k in json.loads(row["keywords"]) if k != keyword]
    c.execute("UPDATE threat_types SET keywords=? WHERE key=?", (json.dumps(keywords), key))
    c.commit()
    c.close()


def set_channel_enabled(key: str, enabled: bool):
    c = _conn()
    c.execute("UPDATE channels SET enabled=? WHERE key=?", (1 if enabled else 0, key))
    c.commit()
    c.close()


def add_channel(key: str, label: str, enabled: bool = True):
    c = _conn()
    c.execute(
        "INSERT OR REPLACE INTO channels (key, label, enabled) VALUES (?, ?, ?)",
        (key, label, 1 if enabled else 0),
    )
    c.commit()
    c.close()


def add_join_request(raw_input: str) -> int:
    c = _conn()
    cur = c.execute(
        "INSERT INTO join_requests (raw_input, status, created_ts) VALUES (?, 'pending', ?)",
        (raw_input, time.time()),
    )
    c.commit()
    rid = cur.lastrowid
    c.close()
    return rid


def get_pending_join_requests():
    c = _conn()
    rows = c.execute("SELECT * FROM join_requests WHERE status='pending' ORDER BY id").fetchall()
    c.close()
    return [dict(r) for r in rows]


def set_join_request_result(request_id: int, status: str, result: str):
    c = _conn()
    c.execute(
        "UPDATE join_requests SET status=?, result=? WHERE id=?",
        (status, result, request_id),
    )
    c.commit()
    c.close()


def get_join_requests_recent(limit: int = 20):
    c = _conn()
    rows = c.execute("SELECT * FROM join_requests ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    c.close()
    return [dict(r) for r in rows]


def get_user(phone: str):
    c = _conn()
    row = c.execute("SELECT * FROM users WHERE phone=?", (phone,)).fetchone()
    c.close()
    return dict(row) if row else None


# Matches the browser cookie's max_age — a session token found past this age is
# treated as expired even though nothing ever deletes it proactively.
SESSION_MAX_AGE_SECONDS = 60 * 60 * 24 * 30


def create_session(token: str, phone: str):
    c = _conn()
    c.execute("INSERT INTO sessions (token, phone, created_ts) VALUES (?, ?, ?)", (token, phone, time.time()))
    c.commit()
    c.close()


def get_session(token: str):
    c = _conn()
    row = c.execute("SELECT * FROM sessions WHERE token=?", (token,)).fetchone()
    c.close()
    if not row:
        return None
    if time.time() - row["created_ts"] > SESSION_MAX_AGE_SECONDS:
        delete_session(token)
        return None
    return dict(row)


def delete_session(token: str):
    c = _conn()
    c.execute("DELETE FROM sessions WHERE token=?", (token,))
    c.commit()
    c.close()
