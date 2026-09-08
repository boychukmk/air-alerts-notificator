def build_active_keywords(config: dict):
    region = config["regions"][config["active_region"]]
    location_keywords = region["target_keywords"] + region["transit_keywords"]

    threat_keywords = []
    for _, t in config["threat_types"].items():
        if t.get("enabled"):
            threat_keywords.extend(t["keywords"])

    return location_keywords, threat_keywords


def build_other_region_keywords(config: dict):
    """Explicit target_keywords of every region EXCEPT the active one — used to detect
    'this message is clearly about a different city' and block cross-message combining."""
    other = []
    for name, region in config["regions"].items():
        if name == config["active_region"]:
            continue
        other.extend(region["target_keywords"])
    return other


def _find_matches(text: str, keywords) -> list[str]:
    lowered = text.lower()
    return [kw for kw in keywords if kw in lowered]


# A real-time launch/inbound-threat post is short and imperative ("Балістика на
# Київ"). Long posts are almost always nightly summaries, situational recaps, or
# "stay alert" advisories — genuine keyword hits, zero actionable urgency.
MAX_ALERT_LENGTH = 200

# Reassurance / all-clear phrasing ("жодна балістика не прямує", "відбій") still
# contains the threat+location keywords but means the opposite of an alert.
NEGATION_PATTERNS = [
    "не прямує", "не летить", "не летять", "не зафіксован", "не підтвердж",
    "відбій", "немає загроз", "загрози немає", "без загроз", "скасован", "хибн",
    "наразі чисто", "поки чисто", "вже чисто",
]


FOOTER_LINE_MARKERS = ["•", "http://", "https://", "t.me/"]


def _strip_footer(text: str) -> str:
    """Channel signature/cross-promo blocks — bullet-separated links to sister
    channels ("💙 Дніпро Alerts • 💛 Київ Alerts") or donate/join URLs — can contain
    city names or other keywords unrelated to the actual alert content. Left in,
    a single such line can make a message match every region regardless of what
    the message actually says. Drop any line carrying one of these markers before
    matching. Best-effort: covers footer styles observed in events.db so far,
    not a general footer detector — extend the marker list as new channels'
    signature formats show up as false positives."""
    return "\n".join(
        line for line in text.split("\n")
        if not any(marker in line for marker in FOOTER_LINE_MARKERS)
    )


def classify_window(texts, location_keywords, threat_keywords, other_region_keywords):
    """texts: recent messages from one channel, oldest first, current message last.

    Priority 1: a single message containing BOTH a threat and our location keyword
    always fires — even if it also mentions another city (real multi-target reports).

    Priority 2: combine the whole window, but only if no message in it explicitly
    names a different city — avoids stitching together unrelated posts.
    """
    texts = [_strip_footer(t) for t in texts]

    # Drop long/negated messages BEFORE either check — otherwise a message
    # rejected by the single-message loop still slips through via the combined
    # fallback below, since that re-scans the same (unfiltered) text.
    lowered_texts = [
        t.lower() for t in texts
        if len(t) <= MAX_ALERT_LENGTH and not any(p in t.lower() for p in NEGATION_PATTERNS)
    ]
    if not lowered_texts:
        return None

    for t in lowered_texts:
        threats = [kw for kw in threat_keywords if kw in t]
        locs = [kw for kw in location_keywords if kw in t]
        if threats and locs:
            return {"matched_threats": threats, "matched_location": locs, "combined": False}

    conflict = any(
        any(kw in t for kw in other_region_keywords) for t in lowered_texts
    )
    if conflict:
        return None

    combined = " ".join(lowered_texts)
    threats = [kw for kw in threat_keywords if kw in combined]
    locs = [kw for kw in location_keywords if kw in combined]
    if threats and locs:
        return {"matched_threats": threats, "matched_location": locs, "combined": True}

    return None
