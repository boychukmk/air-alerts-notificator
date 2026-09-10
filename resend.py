import asyncio
import sys

from telethon.tl.functions.auth import ResendCodeRequest

from telegram_client import make_client


async def resend(phone: str, phone_code_hash: str):
    client = make_client()
    await client.connect()
    result = await client(ResendCodeRequest(phone_number=phone, phone_code_hash=phone_code_hash))
    print(f"RESENT type={result.type} phone_code_hash={result.phone_code_hash}")
    await client.disconnect()


if __name__ == "__main__":
    phone = sys.argv[1]
    phone_code_hash = sys.argv[2]
    asyncio.run(resend(phone, phone_code_hash))
