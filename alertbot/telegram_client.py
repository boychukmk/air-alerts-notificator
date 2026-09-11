import os

from telethon import TelegramClient

from alertbot.paths import DATA_DIR

SESSION_PATH = str(DATA_DIR / "session")


def make_client() -> TelegramClient:
    api_id = int(os.environ["TG_API_ID"])
    api_hash = os.environ["TG_API_HASH"]
    return TelegramClient(SESSION_PATH, api_id, api_hash)
