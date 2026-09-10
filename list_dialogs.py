import asyncio

from telegram_client import make_client


async def main():
    client = make_client()
    await client.start()
    async for dialog in client.iter_dialogs():
        print(f"id={dialog.id} title={dialog.title!r} is_group={dialog.is_group} is_channel={dialog.is_channel}")
    await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
