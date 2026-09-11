from alertbot.dedup import InMemoryDedup
from alertbot.monitor import evaluate_message

THREAT_KEYWORDS = ["балістик", "ракет"]

KYIV: dict = {
    "label": "Київ",
    "location_keywords": ["київ"],
    "other_region_keywords": ["дніпро"],
    "ntfy_topic": "alert-kyiv-test",
}
DNIPRO: dict = {
    "label": "Дніпро",
    "location_keywords": ["дніпро"],
    "other_region_keywords": ["київ"],
    "ntfy_topic": "alert-dnipro-test",
}


def test_no_actions_for_irrelevant_message():
    dedup = InMemoryDedup(window_seconds=180)
    actions = evaluate_message("Гарного дня!", dedup, {"kyiv": KYIV}, THREAT_KEYWORDS, {}, now=0)
    assert actions == []


def test_matching_message_fires_new_event():
    dedup = InMemoryDedup(window_seconds=180)
    last_alert: dict[str, float] = {}
    actions = evaluate_message("Балістика на Київ", dedup, {"kyiv": KYIV}, THREAT_KEYWORDS, last_alert, now=1000)

    assert len(actions) == 1
    assert actions[0]["region_key"] == "kyiv"
    assert actions[0]["is_new_event"] is True
    assert last_alert["kyiv"] == 1000


def test_second_message_within_cooldown_is_confirm_not_new_event():
    dedup = InMemoryDedup(window_seconds=180)
    last_alert: dict[str, float] = {}
    evaluate_message("Балістика на Київ", dedup, {"kyiv": KYIV}, THREAT_KEYWORDS, last_alert, now=1000)

    actions = evaluate_message(
        "Ще балістика на Київ", dedup, {"kyiv": KYIV}, THREAT_KEYWORDS, last_alert, now=1010, cooldown_seconds=120
    )
    assert len(actions) == 1
    assert actions[0]["is_new_event"] is False
    # cooldown timestamp isn't bumped by a confirm — the original launch still anchors it
    assert last_alert["kyiv"] == 1000


def test_message_after_cooldown_expires_fires_new_event_again():
    dedup = InMemoryDedup(window_seconds=180)
    last_alert: dict[str, float] = {"kyiv": 1000}

    actions = evaluate_message(
        "Ще балістика на Київ", dedup, {"kyiv": KYIV}, THREAT_KEYWORDS, last_alert, now=1200, cooldown_seconds=120
    )
    assert actions[0]["is_new_event"] is True
    assert last_alert["kyiv"] == 1200


def test_cooldown_is_independent_per_region():
    dedup = InMemoryDedup(window_seconds=180)
    last_alert: dict[str, float] = {"kyiv": 1000}

    actions = evaluate_message(
        "Балістика на Дніпро", dedup, {"kyiv": KYIV, "dnipro": DNIPRO}, THREAT_KEYWORDS, last_alert, now=1010
    )
    assert len(actions) == 1
    assert actions[0]["region_key"] == "dnipro"
    assert actions[0]["is_new_event"] is True


def test_duplicate_text_produces_no_actions():
    dedup = InMemoryDedup(window_seconds=180)
    last_alert: dict[str, float] = {}
    evaluate_message("Балістика на Київ", dedup, {"kyiv": KYIV}, THREAT_KEYWORDS, last_alert, now=1000)

    actions = evaluate_message("Балістика на Київ", dedup, {"kyiv": KYIV}, THREAT_KEYWORDS, last_alert, now=1001)
    assert actions == []


def test_multiple_regions_can_match_the_same_message():
    dedup = InMemoryDedup(window_seconds=180)
    last_alert: dict[str, float] = {}
    text = "Балістика на Київ і Дніпро одночасно"

    actions = evaluate_message(text, dedup, {"kyiv": KYIV, "dnipro": DNIPRO}, THREAT_KEYWORDS, last_alert, now=1000)

    region_keys = {a["region_key"] for a in actions}
    assert region_keys == {"kyiv", "dnipro"}


def test_empty_text_produces_no_actions():
    dedup = InMemoryDedup(window_seconds=180)
    actions = evaluate_message("", dedup, {"kyiv": KYIV}, THREAT_KEYWORDS, {}, now=0)
    assert actions == []
