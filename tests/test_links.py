from types import SimpleNamespace

from alertbot.links import build_message_link


def test_link_for_public_channel_uses_username():
    chat = SimpleNamespace(username="kyiv_alerts", id=-1001234567890)
    assert build_message_link(chat, 42) == "https://t.me/kyiv_alerts/42"


def test_link_for_private_channel_uses_internal_id():
    chat = SimpleNamespace(username=None, id=-1001234567890)
    assert build_message_link(chat, 42) == "https://t.me/c/1234567890/42"


def test_link_none_when_id_unrecognized():
    chat = SimpleNamespace(username=None, id=12345)
    assert build_message_link(chat, 42) is None
