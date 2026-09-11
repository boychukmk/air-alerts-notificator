import re
from typing import TypedDict


class ClassificationResult(TypedDict):
    matched_threats: list[str]
    matched_location: list[str]
    combined: bool


def build_active_keywords(config: dict) -> tuple[list[str], list[str]]:
    region = config["regions"][config["active_region"]]
    location_keywords = region["target_keywords"] + region["transit_keywords"]

    threat_keywords = []
    for _, t in config["threat_types"].items():
        if t.get("enabled"):
            threat_keywords.extend(t["keywords"])

    return location_keywords, threat_keywords


def build_other_region_keywords(config: dict) -> list[str]:
    other = []
    for name, region in config["regions"].items():
        if name == config["active_region"]:
            continue
        other.extend(region["target_keywords"])
    return other


def _find_matches(text: str, keywords) -> list[str]:
    lowered = text.lower()
    return [kw for kw in keywords if kw in lowered]


MAX_ALERT_LENGTH = 200

# Matched by STEM, not exact phrase — one entry covers every tense/person conjugation.
# Category 1: negated motion/confirmation ("не прямує/прямують", "не зафіксовано").
_NEGATED_VERB_STEMS = ["прям", "лет", "рух", "наближ", "заход", "зафіксов", "підтвердж"]
_NEGATED_VERB_RE = re.compile(r"не\s+\w*(?:" + "|".join(_NEGATED_VERB_STEMS) + r")\w*")
# Category 2: all-clear state ("наразі чисто", "поки спокійно").
_ALL_CLEAR_RE = re.compile(r"(наразі|поки|вже|зараз)\w*\s+\w*(чист|спокійн|тих)\w*")
# Category 3: explicit no-threat statement ("без загроз", "відбій", "хибна тривога").
_NO_THREAT_RE = re.compile(r"без\s+загроз|загроз\w*\s+нема|нема\w*\s+загроз|скасован|хибн|відбій")
# Category 4: if-then hypothetical. "можливо"/"ризик" excluded — those also appear in real warnings.
_CONDITIONAL_RE = re.compile(r"\bякщо\b.*\bто\b")


def _is_negated(lowered_text: str) -> bool:
    return bool(
        _NEGATED_VERB_RE.search(lowered_text)
        or _ALL_CLEAR_RE.search(lowered_text)
        or _NO_THREAT_RE.search(lowered_text)
        or _CONDITIONAL_RE.search(lowered_text)
    )


FOOTER_LINE_MARKERS = ["•", "http://", "https://", "t.me/"]


def _strip_footer(text: str) -> str:
    return "\n".join(
        line for line in text.split("\n")
        if not any(marker in line for marker in FOOTER_LINE_MARKERS)
    )


def classify_window(
    texts: list[str],
    location_keywords: list[str],
    threat_keywords: list[str],
    other_region_keywords: list[str],
) -> ClassificationResult | None:
    """Priority 1: a single message with BOTH threat and location keywords always fires.
    Priority 2: combine the whole window, unless one message names a different city."""
    texts = [_strip_footer(t) for t in texts]

    # Drop long/negated messages before either check, so they can't slip through via the combined fallback.
    lowered_texts = [
        t.lower() for t in texts
        if len(t) <= MAX_ALERT_LENGTH and not _is_negated(t.lower())
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
