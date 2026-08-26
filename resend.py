import asyncio
import os
import sys

from telethon import TelegramClient
from telethon.tl.functions.auth import ResendCodeRequest

API_ID = int(os.environ["TG_API_ID"])
API_HASH = os.environ["TG_API_HASH"]
SESSION_PATH = os.path.join(os.path.dirname(__file__), "kyiv_bot_session")


async def resend(phone: str, phone_code_hash: str):
    client = TelegramClient(SESSION_PATH, API_ID, API_HASH)
    await client.connect()
    result = await client(ResendCodeRequest(phone_number=phone, phone_code_hash=phone_code_hash))
    print(f"RESENT type={result.type} phone_code_hash={result.phone_code_hash}")
    await client.disconnect()


if __name__ == "__main__":
    phone = sys.argv[1]
    phone_code_hash = sys.argv[2]
    asyncio.run(resend(phone, phone_code_hash))
