import json
import sqlite3

import settings_store as store

NEW_REGIONS = {
    "odesa": {
        "label": "Одеса",
        "target_keywords": ["одеса", "одеси", "одесі", "одесою", "одещин"],
        "transit_keywords": ["миколаївщин", "херсонщин"],
    },
    "khmelnytskyi": {
        "label": "Хмельницький",
        "target_keywords": ["хмельницьк", "хмельниччин"],
        "transit_keywords": ["вінниччин", "тернопільщин", "житомирщин"],
    },
}


def main():
    store.init_db()
    c = sqlite3.connect(store.DB_PATH)
    for key, r in NEW_REGIONS.items():
        c.execute(
            "INSERT OR REPLACE INTO regions (key, label, target_keywords, transit_keywords) VALUES (?, ?, ?, ?)",
            (key, r["label"], json.dumps(r["target_keywords"]), json.dumps(r["transit_keywords"])),
        )
        print(f"added region: {key} ({r['label']})")
    c.commit()
    c.close()


if __name__ == "__main__":
    main()
