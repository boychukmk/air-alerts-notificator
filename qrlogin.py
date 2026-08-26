import asyncio
import io
import os

import qrcode
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError

API_ID = int(os.environ["TG_API_ID"])
API_HASH = os.environ["TG_API_HASH"]
SESSION_PATH = os.path.join(os.path.dirname(__file__), "kyiv_bot_session")


async def main():
    client = TelegramClient(SESSION_PATH, API_ID, API_HASH)
    await client.connect()

    qr = await client.qr_login()
    print(f"QR_URL {qr.url}")
    img = qrcode.make(qr.url, box_size=10, border=2)
    png_path = os.path.join(os.path.dirname(__file__), "qr.png")
    img.save(png_path)
    print(f"QR_PNG {png_path}")

    try:
        await qr.wait(timeout=120)
    except SessionPasswordNeededError:
        print("NEED_2FA_PASSWORD")
        await client.disconnect()
        return
    except TimeoutError:
        print("TIMEOUT waiting for QR scan")
        await client.disconnect()
        return

    me = await client.get_me()
    print(f"LOGIN_OK user_id={me.id} username={me.username} phone={me.phone}")
    await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
