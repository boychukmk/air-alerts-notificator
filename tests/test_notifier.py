import httpx
import pytest

from alertbot import notifier


class FakeResponse:
    def __init__(self, status_code: int = 200):
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise httpx.HTTPStatusError("boom", request=None, response=self)


@pytest.mark.asyncio
async def test_send_alert_succeeds_first_try(monkeypatch):
    calls = []

    async def fake_post(url, content, headers):
        calls.append(url)
        return FakeResponse(200)

    monkeypatch.setattr(notifier._client, "post", fake_post)
    await notifier.send_alert("https://ntfy.sh", "topic", "urgent", "Київ", "chan", "text")
    assert len(calls) == 1


@pytest.mark.asyncio
async def test_send_alert_retries_on_failure_then_succeeds(monkeypatch):
    attempts = {"n": 0}

    async def flaky_post(url, content, headers):
        attempts["n"] += 1
        if attempts["n"] < 2:
            return FakeResponse(500)
        return FakeResponse(200)

    monkeypatch.setattr(notifier._client, "post", flaky_post)
    monkeypatch.setattr(notifier.asyncio, "sleep", lambda _: _instant_sleep())
    await notifier.send_alert("https://ntfy.sh", "topic", "urgent", "Київ", "chan", "text")
    assert attempts["n"] == 2


@pytest.mark.asyncio
async def test_send_alert_raises_after_exhausting_retries(monkeypatch):
    async def always_fails(url, content, headers):
        return FakeResponse(500)

    monkeypatch.setattr(notifier._client, "post", always_fails)
    monkeypatch.setattr(notifier.asyncio, "sleep", lambda _: _instant_sleep())
    with pytest.raises(httpx.HTTPStatusError):
        await notifier.send_alert("https://ntfy.sh", "topic", "urgent", "Київ", "chan", "text")


async def _instant_sleep():
    return None


@pytest.mark.asyncio
async def test_send_alert_burst_continues_past_a_failed_seq(monkeypatch):
    sent_seqs = []

    async def fake_send_alert(*args, seq=None, **kwargs):
        if seq == 2:
            raise httpx.HTTPStatusError("boom", request=None, response=None)
        sent_seqs.append(seq)

    monkeypatch.setattr(notifier, "send_alert", fake_send_alert)
    monkeypatch.setattr(notifier.asyncio, "sleep", lambda _: _instant_sleep())
    await notifier.send_alert_burst("https://ntfy.sh", "topic", "urgent", "Київ", "chan", "text", count=3)
    assert sent_seqs == [1, 3]
