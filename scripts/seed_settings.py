import json
import secrets
import sqlite3

from alertbot import settings_store as store
from alertbot.auth import hash_password, new_readable_password

ALLOWED_PHONES = ["380000000000", "380000000001"]  # replace with real phone numbers before running

REGIONS = {
    "kyiv": {
        "label": "Київ",
        "target_keywords": ["київ", "києва", "києву", "києвом", "київщин", "столиц"],
        "transit_keywords": ["чернігівщин", "сумщин", "полтавщин", "черкащин", "житомирщин"],
    },
    "dnipro": {
        "label": "Дніпро",
        "target_keywords": ["дніпро", "дніпра", "дніпру", "дніпропетровщин"],
        "transit_keywords": ["полтавщин", "запорізьк", "харківщин", "кіровоградщин"],
    },
}

THREAT_TYPES = {
    "ballistic": {
        "label": "Балістика",
        "enabled": True,
        "keywords": ["балістик", "іскандер", "кинджал", "аероб"],
    },
    "cruise_missile": {
        "label": "Крилаті ракети",
        "enabled": True,
        "keywords": ["крилат", "ракет", "калібр", "х-101", "х-555", "x-101", "x-555"],
    },
    "shahed": {
        "label": "Шахеди/БПЛА",
        "enabled": False,
        "keywords": ["шахед", "бпла", "дрон", "геран"],
    },
    "aircraft": {
        "label": "Носії (МіГ-31 та ін.)",
        "enabled": False,
        "keywords": ["міг-31", "міг-31к", "зліт", "піднял"],
    },
}

CHANNELS = [
    ("vanek_nikolaev", "Николаевский Ванёк"),
    ("kyiv_alerts", "Kyiv Alerts"),
    ("kyiv_vanek", "Київський Іван"),
    ("mediapivden", "Південь"),
    ("monitorwarr", "monitoring"),
    ("raketa_trevoga", "Чому тривога | Радар"),
    ("-5472055532", "Test"),
]


def main():
    store.init_db()
    c = sqlite3.connect(store.DB_PATH)

    for key, r in REGIONS.items():
        c.execute(
            "INSERT OR REPLACE INTO regions (key, label, target_keywords, transit_keywords) VALUES (?, ?, ?, ?)",
            (key, r["label"], json.dumps(r["target_keywords"]), json.dumps(r["transit_keywords"])),
        )

    for key, t in THREAT_TYPES.items():
        c.execute(
            "INSERT OR REPLACE INTO threat_types (key, label, enabled, keywords) VALUES (?, ?, ?, ?)",
            (key, t["label"], 1 if t["enabled"] else 0, json.dumps(t["keywords"])),
        )

    for key, label in CHANNELS:
        c.execute(
            "INSERT OR REPLACE INTO channels (key, label, enabled) VALUES (?, ?, 1)",
            (key, label),
        )

    c.execute("INSERT OR REPLACE INTO app_state (key, value) VALUES ('active_region', 'kyiv')")
    c.execute(
        "INSERT OR REPLACE INTO app_state (key, value) VALUES ('ntfy_topic', ?)",
        (f"alert-{secrets.token_hex(16)}",),
    )
    c.execute("INSERT OR REPLACE INTO app_state (key, value) VALUES ('ntfy_server', 'https://ntfy.sh')")

    print("Users (SAVE THESE — shown once):")
    for phone in ALLOWED_PHONES:
        password = new_readable_password()
        pw_hash, salt = hash_password(password)
        c.execute(
            "INSERT OR REPLACE INTO users (phone, password_hash, salt, name) VALUES (?, ?, ?, ?)",
            (phone, pw_hash, salt, None),
        )
        print(f"  phone={phone}  password={password}")

    c.commit()
    c.close()


if __name__ == "__main__":
    main()
