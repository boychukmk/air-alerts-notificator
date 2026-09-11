import asyncio
import logging

import httpx

log = logging.getLogger("notifier")
_client = httpx.AsyncClient(timeout=5.0)

SEND_RETRIES = 3
SEND_RETRY_BACKOFF_SECONDS = 1.0


async def send_alert(
    ntfy_server: str, ntfy_topic: str, priority: str, region_label: str, channel_name: str, text: str,
    link: str | None = None, seq: int | None = None,
) -> None:
    url = f"{ntfy_server}/{ntfy_topic}"

    title = f"Загроза: {region_label}" + (f" ({seq})" if seq else "")
    body = f"[{channel_name}] {text[:400]}"

    headers = {
        b"Title": title.encode("utf-8"),
        b"Priority": priority.encode("utf-8"),
        b"Tags": b"rotating_light",
    }
    if link:
        headers[b"Click"] = link.encode("utf-8")
        body += f"\n\n{link}"

    for attempt in range(1, SEND_RETRIES + 1):
        try:
            resp = await _client.post(url, content=body.encode("utf-8"), headers=headers)
            resp.raise_for_status()
            return
        except httpx.HTTPError:
            if attempt == SEND_RETRIES:
                raise
            log.warning("ntfy send attempt %d/%d failed, retrying", attempt, SEND_RETRIES)
            await asyncio.sleep(SEND_RETRY_BACKOFF_SECONDS * attempt)


async def send_alert_burst(
    ntfy_server: str, ntfy_topic: str, priority: str, region_label: str, channel_name: str, text: str,
    link: str | None = None, count: int = 10, interval_seconds: float = 1.0,
) -> None:
    for i in range(1, count + 1):
        try:
            await send_alert(ntfy_server, ntfy_topic, priority, region_label, channel_name, text, link=link, seq=i)
        except Exception:
            log.exception("burst send #%d failed", i)
        if i < count:
            await asyncio.sleep(interval_seconds)
