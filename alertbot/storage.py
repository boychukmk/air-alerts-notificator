import sqlite3
import time


class EventLog:
    """Audit log — written AFTER the alert is sent, never blocks the alert path."""

    def __init__(self, db_path: str) -> None:
        self.conn = sqlite3.connect(db_path)
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts REAL NOT NULL,
                channel TEXT NOT NULL,
                text TEXT NOT NULL,
                matched_threats TEXT,
                matched_location TEXT,
                alerted INTEGER NOT NULL
            )
            """
        )
        self.conn.commit()

    def log(
        self,
        channel: str,
        text: str,
        matched_threats: list[str] | None,
        matched_location: list[str] | None,
        alerted: bool,
    ) -> None:
        self.conn.execute(
            "INSERT INTO events (ts, channel, text, matched_threats, matched_location, alerted) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (
                time.time(),
                channel,
                text,
                ",".join(matched_threats) if matched_threats else None,
                ",".join(matched_location) if matched_location else None,
                1 if alerted else 0,
            ),
        )
        self.conn.commit()
