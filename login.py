import argparse
import asyncio

from telethon.errors import SessionPasswordNeededError

from telegram_client import make_client


async def request_code(phone: str):
    client = make_client()
    await client.connect()
    sent = await client.send_code_request(phone)
    print(f"CODE_REQUESTED phone_code_hash={sent.phone_code_hash}")
    await client.disconnect()


async def confirm_code(phone: str, code: str, phone_code_hash: str, password: str | None):
    client = make_client()
    await client.connect()
    try:
        await client.sign_in(phone=phone, code=code, phone_code_hash=phone_code_hash)
    except SessionPasswordNeededError:
        if not password:
            print("NEED_2FA_PASSWORD")
            await client.disconnect()
            return
        await client.sign_in(password=password)
    me = await client.get_me()
    print(f"LOGIN_OK user_id={me.id} username={me.username} phone={me.phone}")
    await client.disconnect()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)

    p1 = sub.add_parser("request")
    p1.add_argument("phone")

    p2 = sub.add_parser("confirm")
    p2.add_argument("phone")
    p2.add_argument("code")
    p2.add_argument("phone_code_hash")
    p2.add_argument("--password", default=None)

    args = parser.parse_args()

    if args.cmd == "request":
        asyncio.run(request_code(args.phone))
    elif args.cmd == "confirm":
        asyncio.run(confirm_code(args.phone, args.code, args.phone_code_hash, args.password))
