import asyncio
import os
import yaml

from telethon import TelegramClient
from telethon.tl.functions.channels import JoinChannelRequest

API_ID = int(os.environ["TG_API_ID"])
API_HASH = os.environ["TG_API_HASH"]
SESSION_PATH = os.path.join(os.path.dirname(__file__), "session")
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.yaml")


async def main():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    client = TelegramClient(SESSION_PATH, API_ID, API_HASH)
    await client.start()

    for channel in config["telegram"]["channels"]:
        try:
            await client(JoinChannelRequest(channel))
            print(f"joined: {channel}")
        except Exception as e:
            print(f"FAILED {channel}: {e}")
        await asyncio.sleep(2)  # avoid Telegram flood limits on bulk-join

    await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
