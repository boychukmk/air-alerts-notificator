import asyncio
import logging
from typing import Any, TypedDict

from telethon import events
from telethon.errors import UserAlreadyParticipantError
from telethon.tl.functions.channels import JoinChannelRequest
from telethon.tl.functions.messages import ImportChatInviteRequest

from alertbot import settings_store as store
from alertbot.channel_input import parse_channel_input
from alertbot.dedup import InMemoryDedup
from alertbot.filters import ClassificationResult, classify_window
from alertbot.links import build_message_link
from alertbot.notifier import send_alert_burst
from alertbot.paths import DATA_DIR
from alertbot.storage import EventLog
from alertbot.telegram_client import make_client

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s [%(name)s] %(message)s")
log = logging.getLogger("monitor")

REFRESH_SECONDS = 5
GLOBAL_ALERT_COOLDOWN_SECONDS = 120


class RegionConfig(TypedDict):
    label: str
    location_keywords: list[str]
    other_region_keywords: list[str]
    ntfy_topic: str


class LiveConfig:
    """Polls SQLite settings; every enabled region is evaluated independently per message."""

    def __init__(self) -> None:
        self.state: dict[str, Any] | None = None
        self.threat_keywords: list[str] = []
        self.enabled_channel_keys: set[str] = set()
        self.enabled_regions: dict[str, RegionConfig] = {}
        self.ntfy_server = "https://ntfy.sh"
        self.ntfy_priority = "urgent"
        self.refresh()

    def refresh(self) -> None:
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

    async def refresh_loop(self) -> None:
        while True:
            await asyncio.sleep(REFRESH_SECONDS)
            try:
                self.refresh()
            except Exception:
                log.exception("config refresh failed")


class AlertAction(TypedDict):
    region_key: str
    region: RegionConfig
    match: ClassificationResult
    is_new_event: bool


def evaluate_message(
    text: str,
    dedup: InMemoryDedup,
    enabled_regions: dict[str, RegionConfig],
    threat_keywords: list[str],
    last_alert_monotonic: dict[str, float],
    now: float,
    cooldown_seconds: float = GLOBAL_ALERT_COOLDOWN_SECONDS,
) -> list[AlertAction]:
    """Pure — no network/DB I/O — so it's unit testable without a live Telethon client."""
    if not text or dedup.is_duplicate(text):
        return []

    actions: list[AlertAction] = []
    for region_key, region in enabled_regions.items():
        match = classify_window(
            [text], region["location_keywords"], threat_keywords, region["other_region_keywords"]
        )
        if not match:
            continue

        last = last_alert_monotonic.get(region_key, -1e9)
        is_new_event = (now - last) > cooldown_seconds
        if is_new_event:
            last_alert_monotonic[region_key] = now

        actions.append({"region_key": region_key, "region": region, "match": match, "is_new_event": is_new_event})

    return actions


async def process_join_requests(client: Any) -> None:
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


async def main() -> None:
    store.init_db()
    live = LiveConfig()

    log.info("enabled_regions=%s", list(live.enabled_regions.keys()))
    log.info("threat_keywords=%s", live.threat_keywords)
    log.info("enabled_channels=%s", live.enabled_channel_keys)

    dedup = InMemoryDedup(window_seconds=180)
    event_log = EventLog(str(DATA_DIR / "events.db"))

    client = make_client()
    background_tasks: set[asyncio.Task] = set()

    last_alert_monotonic: dict[str, float] = {}

    @client.on(events.NewMessage())
    async def handler(event: Any) -> None:
        chat = await event.get_chat()
        chat_key = getattr(chat, "username", None) or str(event.chat_id)

        if chat_key not in live.enabled_channel_keys:
            return

        text = event.raw_text or ""
        channel_label = getattr(chat, "username", None) or getattr(chat, "title", None) or str(event.chat_id)
        message_link = build_message_link(chat, event.message.id)

        now = asyncio.get_event_loop().time()
        actions = evaluate_message(
            text, dedup, live.enabled_regions, live.threat_keywords, last_alert_monotonic, now
        )

        for action in actions:
            region_key, region, match, is_new_event = (
                action["region_key"], action["region"], action["match"], action["is_new_event"]
            )

            if is_new_event:
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
