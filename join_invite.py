import asyncio
import os
import sys

from telethon import TelegramClient
from telethon.tl.functions.messages import ImportChatInviteRequest
from telethon.errors import UserAlreadyParticipantError

API_ID = int(os.environ["TG_API_ID"])
API_HASH = os.environ["TG_API_HASH"]
SESSION_PATH = os.path.join(os.path.dirname(__file__), "session")


async def main(invite_hash: str):
    client = TelegramClient(SESSION_PATH, API_ID, API_HASH)
    await client.start()

    try:
        result = await client(ImportChatInviteRequest(invite_hash))
        chat = result.chats[0]
    except UserAlreadyParticipantError:
        # already a member — resolve via dialogs
        chat = None
        async for dialog in client.iter_dialogs():
            if dialog.entity.id and getattr(dialog.entity, "title", None):
                pass
        print("ALREADY_MEMBER — resolve id via dialogs manually")
        await client.disconnect()
        return

    print(f"JOINED id={chat.id} title={chat.title}")
    await client.disconnect()


if __name__ == "__main__":
    # accepts either the raw hash or the full https://t.me/+HASH link
    arg = sys.argv[1]
    invite_hash = arg.split("+")[-1] if "+" in arg else arg
    asyncio.run(main(invite_hash))
