import asyncio
import logging

import httpx

log = logging.getLogger("notifier")
_client = httpx.AsyncClient(timeout=5.0)


async def send_alert(
    ntfy_server: str, ntfy_topic: str, priority: str, region_label: str, channel_name: str, text: str,
    link: str | None = None, seq: int | None = None,
):
    url = f"{ntfy_server}/{ntfy_topic}"

    title = f"Загроза: {region_label}" + (f" ({seq})" if seq else "")
    body = f"[{channel_name}] {text[:400]}"

    headers = {
        "Title": title.encode("utf-8"),
        "Priority": priority,
        "Tags": "rotating_light",
    }
    if link:
        headers["Click"] = link.encode("utf-8")  # tapping the notification opens the source message
        body += f"\n\n{link}"

    await _client.post(url, content=body.encode("utf-8"), headers=headers)


async def send_alert_burst(
    ntfy_server: str, ntfy_topic: str, priority: str, region_label: str, channel_name: str, text: str,
    link: str | None = None, count: int = 10, interval_seconds: float = 1.0,
):
    """Fires `count` notifications spaced out, so iOS doesn't collapse them into one
    silent group — acts like a repeating alarm until the person notices."""
    for i in range(1, count + 1):
        try:
            await send_alert(ntfy_server, ntfy_topic, priority, region_label, channel_name, text, link=link, seq=i)
        except Exception:
            log.exception("burst send #%d failed", i)
        if i < count:
            await asyncio.sleep(interval_seconds)
