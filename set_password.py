import sqlite3
import sys

import settings_store as store
from auth import hash_password


def main(phone: str, new_password: str):
    pw_hash, salt = hash_password(new_password)
    c = sqlite3.connect(store.DB_PATH)
    cur = c.execute("UPDATE users SET password_hash=?, salt=? WHERE phone=?", (pw_hash, salt, phone))
    c.commit()
    print(f"updated rows: {cur.rowcount}")
    c.close()


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
