import asyncio
import os

from telethon import TelegramClient

API_ID = int(os.environ["TG_API_ID"])
API_HASH = os.environ["TG_API_HASH"]
SESSION_PATH = os.path.join(os.path.dirname(__file__), "session")


async def main():
    client = TelegramClient(SESSION_PATH, API_ID, API_HASH)
    await client.start()
    async for dialog in client.iter_dialogs():
        print(f"id={dialog.id} title={dialog.title!r} is_group={dialog.is_group} is_channel={dialog.is_channel}")
    await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
