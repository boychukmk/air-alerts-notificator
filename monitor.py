import asyncio
import logging
import os

from telethon import events
from telethon.errors import UserAlreadyParticipantError
from telethon.tl.functions.channels import JoinChannelRequest
from telethon.tl.functions.messages import ImportChatInviteRequest

import settings_store as store
from channel_input import parse_channel_input
from dedup import InMemoryDedup
from filters import classify_window
from links import build_message_link
from notifier import send_alert_burst
from storage import EventLog
from telegram_client import make_client

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s [%(name)s] %(message)s")
log = logging.getLogger("monitor")

REFRESH_SECONDS = 5
GLOBAL_ALERT_COOLDOWN_SECONDS = 120


class LiveConfig:
    """Polls SQLite settings. Every ENABLED region is evaluated independently and in
    parallel for each incoming message — Kyiv and Odesa and Khmelnytskyi can all be
    live at once, each with its own keywords and its own ntfy topic."""

    def __init__(self):
        self.state = None
        self.threat_keywords = []
        self.enabled_channel_keys = set()
        self.enabled_regions = {}  # key -> {label, location_keywords, other_region_keywords, ntfy_topic}
        self.ntfy_server = "https://ntfy.sh"
        self.ntfy_priority = "urgent"
        self.refresh()

    def refresh(self):
        state = store.get_state()
        self.state = state
        self.ntfy_server = state["ntfy_server"]
        self.ntfy_priority = state["ntfy_priority"]

        self.threat_keywords = []
        for t in state["threat_types"].values():
            if t["enabled"]:
                self.threat_keywords.extend(t["keywords"])

        enabled_region_keys = [k for k, r in state["regions"].items() if r["enabled"]]

        self.enabled_regions = {}
        for key in enabled_region_keys:
            r = state["regions"][key]
            other = []
            for other_key, other_r in state["regions"].items():
                if other_key != key:
                    other.extend(other_r["target_keywords"])
            self.enabled_regions[key] = {
                "label": r["label"],
                "location_keywords": r["target_keywords"] + r["transit_keywords"],
                "other_region_keywords": other,
                "ntfy_topic": r["ntfy_topic"],
            }

        self.enabled_channel_keys = {c["key"] for c in state["channels"] if c["enabled"]}

    async def refresh_loop(self):
        while True:
            await asyncio.sleep(REFRESH_SECONDS)
            try:
                self.refresh()
            except Exception:
                log.exception("config refresh failed")


async def process_join_requests(client):
    while True:
        await asyncio.sleep(5)
        try:
            for req in store.get_pending_join_requests():
                kind, value = parse_channel_input(req["raw_input"])
                try:
                    if kind == "invite":
                        result = await client(ImportChatInviteRequest(value))
                        chat = result.chats[0]
                    else:
                        result = await client(JoinChannelRequest(value))
                        chat = result.chats[0]

                    key = getattr(chat, "username", None) or str(chat.id)
                    label = getattr(chat, "title", None) or key
                    store.add_channel(key, label, enabled=True)
                    store.set_join_request_result(req["id"], "done", f"joined: {label}")
                    log.info("added channel %s (%s)", label, key)
                except UserAlreadyParticipantError:
                    store.set_join_request_result(req["id"], "done", "already a member")
                except Exception as e:
                    store.set_join_request_result(req["id"], "failed", str(e))
                    log.warning("join failed for %r: %s", req["raw_input"], e)
        except Exception:
            log.exception("join request loop error")


async def main():
    store.init_db()
    live = LiveConfig()

    log.info("enabled_regions=%s", list(live.enabled_regions.keys()))
    log.info("threat_keywords=%s", live.threat_keywords)
    log.info("enabled_channels=%s", live.enabled_channel_keys)

    dedup = InMemoryDedup(window_seconds=180)
    event_log = EventLog(os.path.join(os.path.dirname(__file__), "events.db"))

    client = make_client()
    background_tasks = set()

    # Per-region cooldown: if 6 channels all confirm the same launch toward the SAME
    # city within seconds of each other, that's one event, not six bursts. A launch
    # toward a different city at the same time is independent and still fires.
    last_alert_monotonic: dict[str, float] = {}

    # No chats= filter — listen to everything the account is a member of,
    # then check membership against the live enabled-channel set per message.
    @client.on(events.NewMessage())
    async def handler(event):
        chat = await event.get_chat()
        chat_key = getattr(chat, "username", None) or str(event.chat_id)

        if chat_key not in live.enabled_channel_keys:
            return

        text = event.raw_text or ""
        if not text:
            return

        channel_label = getattr(chat, "username", None) or getattr(chat, "title", None) or str(event.chat_id)
        message_link = build_message_link(chat, event.message.id)

        if dedup.is_duplicate(text):
            return

        # Cross-message combining ("Балістика" + separate "Курс на Київ") was tried
        # and reverted — on busy channels it kept stitching together unrelated posts
        # (e.g. a Poltava-only report + an unrelated nearby "Київ" mention), producing
        # false alerts. Threat + location must now be in the SAME message.
        for region_key, region in live.enabled_regions.items():
            match = classify_window(
                [text], region["location_keywords"], live.threat_keywords, region["other_region_keywords"]
            )
            if not match:
                continue

            now = asyncio.get_event_loop().time()
            last = last_alert_monotonic.get(region_key, -1e9)
            is_new_event = (now - last) > GLOBAL_ALERT_COOLDOWN_SECONDS

            if is_new_event:
                last_alert_monotonic[region_key] = now
                task = asyncio.create_task(
                    send_alert_burst(
                        live.ntfy_server, region["ntfy_topic"], live.ntfy_priority,
                        region["label"], channel_label, text, link=message_link, count=5, interval_seconds=1.0,
                    )
                )
                background_tasks.add(task)
                task.add_done_callback(background_tasks.discard)
                log.info("ALERT:%s %s: %s", region_key, channel_label, text[:120])
            else:
                log.info("CONFIRM:%s %s (кулдаун, без нового burst): %s", region_key, channel_label, text[:120])

            event_log.log(
                f"{region_key}/{channel_label}", text, match["matched_threats"], match["matched_location"],
                alerted=is_new_event,
            )

    asyncio.create_task(live.refresh_loop())
    asyncio.create_task(process_join_requests(client))

    await client.start()
    log.info("listening...")
    await client.run_until_disconnected()


if __name__ == "__main__":
    asyncio.run(main())
