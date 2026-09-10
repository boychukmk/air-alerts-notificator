import pytest

from filters import classify_window

LOCATION_KEYWORDS = [
    "київ", "києва", "києву", "києвом", "київщин", "столиц",
    "чернігівщин", "сумщин", "полтавщин", "черкащин",
]
THREAT_KEYWORDS = ["балістик", "крилат", "ракет", "калібр"]
OTHER_REGION_KEYWORDS = ["дніпро", "одеса", "хмельницьк"]


def classify(text):
    return classify_window([text], LOCATION_KEYWORDS, THREAT_KEYWORDS, OTHER_REGION_KEYWORDS)


# Real alerts pulled from events.db during the 2026-09-08 mass attack — these
# must keep firing. Every filter change should be checked against this list.
REAL_ALERTS = [
    "Також балістика на Київ, загалом 6 цілей! Будьте в укритті.",
    "Ще балістика на Київ.",
    "Ще пуски балістики з Брянська на Київ",
    "4 ракети на Київ!",
    "Крилаті ракети заходять через Сумщину",
    "Крилата ракета на Київ. Поки одна.",
    "Балістика Київ.",
    "Ще ракета по тому ж вектору на Чернігівщині.",
    "❗️ 2 групи крилатих ракет повз межу Чернігівщини та Сумщини.",
    "Близько 14 крилатих ракет рухаються поки на Полтавщину.",
    "Група ракет розвертається в бік Київщини. Очікуємо їх згодом…",
    "Область червоний 🟥. З Білої Церкви та зі сходу крилаті ракети. Курс Київ.",
    "За пару хвилин ракети будуть над столицею. В укриття.",
    "З декількох сторін будуть заходити на Київ групи крилатих ракет!",
    "Через Білу Церкву на Київ балістика.",
]

# Messages that contain both a threat and a location keyword but must NOT alert —
# each one caused a real false positive at some point in production.
FALSE_POSITIVES = [
    # all-clear state, various phrasing
    "По крилатим над Києвом наразі чисто, доволі багато збили наші хлопці сьогодні.",
    "Поки спокійно на небі над Києвом.",
    # explicit no-threat statement
    "По ракетам без загроз. Навколо столиці реактивний. З Чернігівщини ще декілька.",
    # negated motion verb, including an inflected form the old exact-phrase list missed
    "Київчата, жодна балістика до нас не прямує зараз.",
    "Балістика не прямують у бік Києва.",
    # if-then conditional / hypothetical
    "Якщо калібри атакуватимуть Київ, то буде великий шанс комбінованого удару разом з балістикою.",
    # cancellation / false alarm
    "Балістика на Київ скасована, це була хибна тривога.",
]

# Long recap/summary posts must not alert regardless of keyword hits.
LONG_SUMMARY = (
    "Протягом ночі зберігається ризик застосування балістики по Києву та області. "
    "Русня намагатиметься завдавати ударів по об'єктах і складах. "
    "Не варто нехтувати сигналами тривоги навіть під час повторних або короткотривалих сповіщень."
)

# Footer/cross-promo lines must not create false matches for other cities.
FOOTER_CASES = [
    "Балістика на Дніпро.\n💙 Дніпро Alerts • 💛 Київ Alerts",
    "Ракета на Одесу.\nhttps://t.me/some_channel",
]


@pytest.mark.parametrize("text", REAL_ALERTS)
def test_real_alerts_fire(text):
    assert classify(text) is not None, f"should have alerted: {text!r}"


@pytest.mark.parametrize("text", FALSE_POSITIVES)
def test_false_positives_blocked(text):
    assert classify(text) is None, f"should NOT have alerted: {text!r}"


def test_long_summary_blocked():
    assert classify(LONG_SUMMARY) is None


@pytest.mark.parametrize("text", FOOTER_CASES)
def test_footer_does_not_leak_other_city_keywords(text):
    # None of these mention Kyiv/Chernihiv/etc outside the footer, so they must not alert.
    assert classify(text) is None


def test_multi_target_message_with_our_city_still_fires():
    text = "Балістика на Житомир і Київ одночасно."
    result = classify(text)
    assert result is not None
    assert "балістик" in result["matched_threats"]


def test_no_match_without_threat_keyword():
    assert classify("Гарного дня, Києве!") is None


def test_no_match_without_location_keyword():
    assert classify("Балістика летить кудись невідомо куди.") is None
