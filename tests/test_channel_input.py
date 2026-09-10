import pytest

from channel_input import parse_channel_input


@pytest.mark.parametrize("raw,expected", [
    ("@some_channel", ("username", "some_channel")),
    ("some_channel", ("username", "some_channel")),
    ("https://t.me/some_channel", ("username", "some_channel")),
    ("http://t.me/some_channel", ("username", "some_channel")),
    ("https://t.me/+AbCdEf123", ("invite", "AbCdEf123")),
    ("https://t.me/joinchat/AbCdEf123", ("invite", "AbCdEf123")),
    ("+AbCdEf123", ("invite", "AbCdEf123")),
])
def test_parse_channel_input(raw, expected):
    assert parse_channel_input(raw) == expected
