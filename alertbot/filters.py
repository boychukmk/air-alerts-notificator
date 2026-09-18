import re
from typing import TypedDict


class ClassificationResult(TypedDict):
    matched_threats: list[str]
    matched_location: list[str]


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
# Category 5: fundraising/donation appeal riding along on threat+location keywords.
_DONATION_RE = re.compile(
    r"monobank|privat24|patreon|buymeacoffee|підтримати\s+канал|буду\s+вдячн|"
    r"перекаж\w*\s+(грош|кошт|донат)|\bдонат"
)
# Category 6: cross-promotion of another channel/person, not a report of this event.
_CROSS_PROMO_RE = re.compile(
    r"(колег|рекоменду|підпиш\w*ся|підписуйтесь|приєднуйтесь)\w*[\s\S]{0,80}@\w+"
    r"|@\w+[\s\S]{0,80}(колег|рекоменду|підпиш\w*ся|підписуйтесь|приєднуйтесь)\w*"
)
# Shared by categories 7-8: any of these means "happening right now" — never
# exclude a message that has one, even if it also reads like news or a forecast.
_CURRENT_ACTION_RE = re.compile(r"\bзараз\b|\bвже\b|за\s+\d+\s*хв|летит\w*|наближ\w*|\bкурс\b")
# Category 7: reporting an already-completed strike (news, not an in-progress threat).
_PAST_DAMAGE_RE = re.compile(r"вдарил\w*|знищил\w*|поранен\w*|загинул\w*|постраждал\w*|зруйнован\w*")
# Category 8: forecast/speculative risk for later, not a launch happening now.
_FORECAST_RE = re.compile(
    r"прогнозу\w*|плану\w*\s+атакувати|можлив\w*\s+застосуванн\w*|найближч\w*\s*(добами|годин\w*|дні)"
)


def _should_exclude(lowered_text: str) -> bool:
    return bool(
        _NEGATED_VERB_RE.search(lowered_text)
        or _ALL_CLEAR_RE.search(lowered_text)
        or _NO_THREAT_RE.search(lowered_text)
        or _CONDITIONAL_RE.search(lowered_text)
        or _DONATION_RE.search(lowered_text)
        or _CROSS_PROMO_RE.search(lowered_text)
        or (_PAST_DAMAGE_RE.search(lowered_text) and not _CURRENT_ACTION_RE.search(lowered_text))
        or (_FORECAST_RE.search(lowered_text) and not _CURRENT_ACTION_RE.search(lowered_text))
    )


def _effective_transit_matches(lowered_text: str, transit_keywords: list[str]) -> list[str]:
    """A transit region only counts as "on the way to us" when the wording says
    passage ("через"/"повз"/"межу"). "на <transit region>" names it as someone
    else's actual target, not a waypoint — e.g. "ракети на Полтавщину" is a
    Poltava-bound strike, not a sign anything is headed further to Kyiv."""
    matches = []
    for kw in transit_keywords:
        if kw not in lowered_text:
            continue
        targeting = re.search(r"\bна\s+\w*" + re.escape(kw) + r"\w*|\bкурс\s+на\s+\w*" + re.escape(kw) + r"\w*"
                               r"|\bу\s+бік\s+\w*" + re.escape(kw) + r"\w*", lowered_text)
        passage = re.search(r"\bчерез\s+\w*" + re.escape(kw) + r"\w*|\bповз\s+\w*" + re.escape(kw) + r"\w*"
                             r"|\bмежу\s+\w*" + re.escape(kw) + r"\w*", lowered_text)
        if targeting and not passage:
            continue
        matches.append(kw)
    return matches


FOOTER_LINE_MARKERS = ["•", "http://", "https://", "t.me/"]


def _strip_footer(text: str) -> str:
    return "\n".join(
        line for line in text.split("\n")
        if not any(marker in line for marker in FOOTER_LINE_MARKERS)
    )


def _location_matches(text: str, target_keywords: list[str], transit_keywords: list[str]) -> list[str]:
    return [kw for kw in target_keywords if kw in text] + _effective_transit_matches(text, transit_keywords)


def classify_window(
    text: str,
    target_keywords: list[str],
    transit_keywords: list[str],
    threat_keywords: list[str],
) -> ClassificationResult | None:
    """Fires only when a single message names both a threat and a location."""
    text = _strip_footer(text)
    if len(text) > MAX_ALERT_LENGTH:
        return None

    lowered = text.lower()
    if _should_exclude(lowered):
        return None

    threats = [kw for kw in threat_keywords if kw in lowered]
    locs = _location_matches(lowered, target_keywords, transit_keywords)
    if threats and locs:
        return {"matched_threats": threats, "matched_location": locs}

    return None
