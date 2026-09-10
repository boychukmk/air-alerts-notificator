import asyncio

import qrcode
from telethon.errors import SessionPasswordNeededError

from alertbot.paths import DATA_DIR
from alertbot.telegram_client import make_client


async def main():
    client = make_client()
    await client.connect()

    qr = await client.qr_login()
    print(f"QR_URL {qr.url}")
    img = qrcode.make(qr.url, box_size=10, border=2)
    png_path = str(DATA_DIR / "qr.png")
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
