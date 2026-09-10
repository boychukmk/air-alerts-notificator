import asyncio
import sys

from telethon.errors import UserAlreadyParticipantError
from telethon.tl.functions.messages import ImportChatInviteRequest

from telegram_client import make_client


async def main(invite_hash: str):
    client = make_client()
    await client.start()

    try:
        result = await client(ImportChatInviteRequest(invite_hash))
        chat = result.chats[0]
    except UserAlreadyParticipantError:
        print("ALREADY_MEMBER — resolve id via list_dialogs.py")
        await client.disconnect()
        return

    print(f"JOINED id={chat.id} title={chat.title}")
    await client.disconnect()


if __name__ == "__main__":
    # accepts either the raw hash or the full https://t.me/+HASH link
    arg = sys.argv[1]
    invite_hash = arg.split("+")[-1] if "+" in arg else arg
    asyncio.run(main(invite_hash))
