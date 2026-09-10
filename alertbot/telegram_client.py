import os

from telethon import TelegramClient

from alertbot.paths import DATA_DIR

API_ID = int(os.environ["TG_API_ID"])
API_HASH = os.environ["TG_API_HASH"]

# Single shared session file — this is the identity of the monitoring account.
# Every script that logs in, joins channels, or listens for messages must point
# at the same file, or it silently operates on a disconnected Telegram session.
SESSION_PATH = str(DATA_DIR / "session")


def make_client() -> TelegramClient:
    return TelegramClient(SESSION_PATH, API_ID, API_HASH)
