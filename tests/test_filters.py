import pytest

from alertbot.filters import classify_window

TARGET_KEYWORDS = ["київ", "києва", "києву", "києвом", "київщин", "столиц"]
TRANSIT_KEYWORDS = ["чернігівщин", "сумщин", "полтавщин", "черкащин"]
THREAT_KEYWORDS = ["балістик", "крилат", "ракет", "калібр"]


def classify(text):
    return classify_window(text, TARGET_KEYWORDS, TRANSIT_KEYWORDS, THREAT_KEYWORDS)


REAL_ALERTS = [
    "Також балістика на Київ, загалом 6 цілей! Будьте в укритті.",
    "Ще балістика на Київ.",
    "Ще пуски балістики з Брянська на Київ",
    "4 ракети на Київ!",
    "Крилаті ракети заходять через Сумщину",
    "Крилата ракета на Київ. Поки одна.",
    "Балістика Київ.",
    "❗️ 2 групи крилатих ракет повз межу Чернігівщини та Сумщини.",
    "Група ракет розвертається в бік Київщини. Очікуємо їх згодом…",
    "Область червоний 🟥. З Білої Церкви та зі сходу крилаті ракети. Курс Київ.",
    "За пару хвилин ракети будуть над столицею. В укриття.",
    "З декількох сторін будуть заходити на Київ групи крилатих ракет!",
    "Через Білу Церкву на Київ балістика.",
]

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
    # donation appeal riding on threat+location keywords (real message from events.db)
    "Виходи з Брянська \n\nПідтримати канал, буду вдячний Вам:\n\nhttps://base.monobank.ua/4jYdAKEbmcrmLL",
    # cross-promotion of another channel/person, not a report of this event
    "❗️Друзі, одним з перших про рух балістики повідомляє наш колега, військовий ППО «Радник»: @radnyk\n\n"
    "Він вже попередив про всі останні обстріли Києва та області.",
    # retrospective news about an already-completed strike, not an in-progress threat
    "російські покидьки вдарили по багатоповерхівці в Одесі. Наразі відомо про 12 постраждалих. "
    "Ракети йшли дуже низько. Порядка 20м по показниках.",
    "Сьогодні РФ ракетами знищила сортувальний центр мережі магазинів «EVA» в Одесі.",
    # forecast/speculative risk for later, not a launch happening now
    "Рідні, для Київщини цієї ночі прогнозують підвищену небезпеку через можливе застосування балістики, "
    "я буду на звʼязку з вами.",
    "⚡️Ворог планує атакувати Одещину найближчими двома добами балістикою та ракетами онікс.",
    # transit region named as someone else's actual target ("на X"), not a waypoint ("через"/"повз" X)
    "Балістика на Полтавщині, 3 цілі.",
    "Близько 14 крилатих ракет рухаються поки на Полтавщину.",
    "❗️ 3 крилаті ракети на Черкащині західним курсом.",
    "Ще ракета по тому ж вектору на Чернігівщині.",
]

# Long recap/summary posts must not alert regardless of keyword hits.
LONG_SUMMARY = (
    "Протягом ночі зберігається ризик застосування балістики по Києву та області. "
    "Русня намагатиметься завдавати ударів по об'єктах і складах. "
    "Не варто нехтувати сигналами тривоги навіть під час повторних або короткотривалих сповіщень."
)

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
