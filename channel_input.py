import re


def parse_channel_input(raw: str):
    """Accepts @username, bare username, https://t.me/username,
    https://t.me/+HASH or https://t.me/joinchat/HASH invite links.
    Returns ("invite", hash) or ("username", name)."""
    s = raw.strip()

    s = re.sub(r"^https?://(www\.)?t\.me/", "", s, flags=re.IGNORECASE)
    s = s.strip("/")

    if s.startswith("+"):
        return "invite", s[1:]
    if s.lower().startswith("joinchat/"):
        return "invite", s.split("/", 1)[1]

    s = s.lstrip("@")
    return "username", s
