def build_message_link(chat, message_id: int):
    username = getattr(chat, "username", None)
    if username:
        return f"https://t.me/{username}/{message_id}"

    chat_id_str = str(getattr(chat, "id", ""))
    if chat_id_str.startswith("-100"):
        internal_id = chat_id_str[4:]
        return f"https://t.me/c/{internal_id}/{message_id}"

    # Legacy basic groups (small negative ids) have no stable public/deep link.
    return None
