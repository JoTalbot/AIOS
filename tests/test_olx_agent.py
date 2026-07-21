"""Tests for the AIOS OLX Android Parser Agent.

The UIAutomator sample dump is embedded as a string on purpose: ``*.xml``
artifacts are git-ignored in this repository as OLX debug files.
"""

from datetime import datetime

from aios_core.modules.olx import (
    AdCard,
    CardParser,
    CompetitorAnalyzer,
    OLXCollector,
    OLXStorage,
    RecommendationEngine,
)
from aios_core.modules.olx.text_utils import (
    is_top_text,
    parse_price,
    parse_published,
)

NODE_ATTRS = (
    'class="android.view.View" package="ua.slando" checkable="false" '
    'checked="false" clickable="false" enabled="true" focusable="false" '
    'focused="false" scrollable="false" long-clickable="false" '
    'password="false" selected="false"'
)

SAMPLE_XML = f"""<?xml version='1.0' encoding='UTF-8' standalone='yes' ?>
<hierarchy rotation="0">
  <node index="0" text="" resource-id="" {NODE_ATTRS} bounds="[0,0][1080,2400]">
    <node index="0" text="МИ ЗНАЙШЛИ 1000 ОГОЛОШЕНЬ" resource-id=""
          {NODE_ATTRS} bounds="[24,60][800,120]"/>
    <node index="1" text="" resource-id="ua.slando:id/adListing_adGridCard"
          {NODE_ATTRS} bounds="[0,140][540,980]">
      <node text="" resource-id="ua.slando:id/ad_grid_card_image"
            content-desc="https://www.olx.ua/d/uk/obyavlenie/bmw-x3-IDz7kLq.html"
            {NODE_ATTRS} bounds="[0,140][540,600]"/>
      <node text="BMW X3 G01 (2017-) - лобове скло, стекло лобовое"
            resource-id="" {NODE_ATTRS} bounds="[16,610][520,680]"/>
      <node text="7 000 грн" resource-id="" {NODE_ATTRS} bounds="[16,690][300,740]"/>
      <node text="Львів" resource-id="" {NODE_ATTRS} bounds="[16,750][300,800]"/>
      <node text="Сьогодні в 11:26" resource-id="" {NODE_ATTRS} bounds="[16,810][400,860]"/>
      <node text="TOP" resource-id="" {NODE_ATTRS} bounds="[420,140][520,190]"/>
    </node>
    <node index="2" text="" resource-id="ua.slando:id/adListing_adGridCard"
          {NODE_ATTRS} bounds="[540,140][1080,980]">
      <node text="Лобове скло Audi A4 B8" resource-id=""
            {NODE_ATTRS} bounds="[560,610][1060,680]"/>
      <node text="Договірна" resource-id="" {NODE_ATTRS} bounds="[560,690][800,740]"/>
      <node text="Київ" resource-id="" {NODE_ATTRS} bounds="[560,750][800,800]"/>
      <node text="Вчора о 18:02" resource-id="" {NODE_ATTRS} bounds="[560,810][900,860]"/>
    </node>
  </node>
</hierarchy>
"""

PAGE_TWO_XML = SAMPLE_XML.replace(
    "BMW X3 G01 (2017-) - лобове скло, стекло лобовое",
    "Лобове скло Mercedes W211 E-class",
    1,
).replace("7 000 грн", "5 500 грн", 1).replace("Львів", "Дніпро", 1)


class FakeADB:
    """ADBController stand-in replaying prepared XML pages."""

    def __init__(self, pages):
        self.pages = list(pages)
        self.commands = []
        self.swipes = 0

    def run(self, command):
        self.commands.append(command)
        return {"code": 0, "stdout": "", "stderr": ""}

    def dump_ui(self, filename="screen.xml"):
        page = self.pages.pop(0) if self.pages else self.last_page
        self.last_page = page
        with open(filename, "w", encoding="utf-8") as fh:
            fh.write(page)
        return {"code": 0, "stdout": "", "stderr": ""}

    def swipe(self, x1, y1, x2, y2, duration=500):
        self.swipes += 1
        return {"code": 0, "stdout": "", "stderr": ""}


NOW = datetime(2026, 7, 21, 15, 0, 0)


# --- text_utils -------------------------------------------------------------


def test_parse_price_formats():
    assert parse_price("7 000 грн") == (7000.0, "UAH")
    assert parse_price("1 500 $") == (1500.0, "USD")
    assert parse_price("$ 2 350") == (2350.0, "USD")
    assert parse_price("900 €") == (900.0, "EUR")
    assert parse_price("1 200,50 грн") == (1200.5, "UAH")


def test_parse_price_non_numeric_labels():
    assert parse_price("Договірна") is None
    assert parse_price("Обмін") is None
    assert parse_price("Безкоштовно") is None
    assert parse_price("BMW X3 G01 (2017-)") is None
    assert parse_price("") is None
    assert parse_price(None) is None


def test_parse_published_relative_and_absolute():
    assert parse_published("Сьогодні в 11:26", now=NOW) == "2026-07-21T11:26:00"
    assert parse_published("Сегодня в 09:05", now=NOW) == "2026-07-21T09:05:00"
    assert parse_published("Вчора о 18:02", now=NOW) == "2026-07-20T18:02:00"
    assert parse_published("Вчера в 23:59", now=NOW) == "2026-07-20T23:59:00"
    assert parse_published("21 липня 2026", now=NOW) == "2026-07-21T00:00:00"
    assert parse_published("3 марта 2026 г.", now=NOW) == "2026-03-03T00:00:00"
    assert parse_published("Київ", now=NOW) is None
    assert parse_published(None, now=NOW) is None


def test_is_top_badge():
    assert is_top_text("TOP")
    assert is_top_text("топ")
    assert not is_top_text("Топлення")
    assert not is_top_text("")


# --- CardParser -------------------------------------------------------------


def test_card_parser_extracts_cards():
    cards = CardParser().parse(SAMPLE_XML, query="лобове скло")

    assert len(cards) == 2

    first = cards[0]
    assert first.title.startswith("BMW X3")
    assert first.price == 7000.0
    assert first.currency == "UAH"
    assert first.city == "Львів"
    assert first.published_text == "Сьогодні в 11:26"
    assert first.published_at is not None
    assert first.is_top is True
    assert first.query == "лобове скло"
    assert first.url == "https://www.olx.ua/d/uk/obyavlenie/bmw-x3-IDz7kLq.html"
    assert first.ad_id == "z7kLq"

    second = cards[1]
    assert second.title == "Лобове скло Audi A4 B8"
    assert second.price is None  # «Договірна»
    assert second.city == "Київ"
    assert second.is_top is False


def test_card_parser_accepts_short_resource_ids_and_paths(tmp_path):
    short_xml = SAMPLE_XML.replace("ua.slando:id/", "")
    cards = CardParser().parse(short_xml)
    assert len(cards) == 2

    dump = tmp_path / "screen.xml"
    dump.write_text(SAMPLE_XML, encoding="utf-8")
    cards_from_file = CardParser().parse(dump)
    assert len(cards_from_file) == 2


def test_card_fingerprint_dedup_key():
    card_a = CardParser.card_from_texts(["Скло лобове", "7 000 грн", "Львів"])
    card_b = CardParser.card_from_texts(["скло лобове", "7 000 грн", "Львів"])
    card_c = CardParser.card_from_texts(["Скло лобове", "8 000 грн", "Львів"])
    assert card_a.fingerprint == card_b.fingerprint
    assert card_a.fingerprint != card_c.fingerprint


# --- OLXCollector -----------------------------------------------------------


def test_collector_collects_dedupes_and_stops():
    adb = FakeADB(pages=[SAMPLE_XML, SAMPLE_XML, SAMPLE_XML])
    collector = OLXCollector(adb=adb)

    cards = collector.collect(query="лобове скло")

    assert len(cards) == 2  # two unique cards, identical pages deduplicated
    assert adb.swipes >= 2  # two idle pages trigger the stop condition


def test_collector_handles_multi_page_feed():
    adb = FakeADB(pages=[SAMPLE_XML, PAGE_TWO_XML, PAGE_TWO_XML, PAGE_TWO_XML])
    collector = OLXCollector(adb=adb)
    pages_seen = []

    cards = collector.collect(
        query="лобове скло",
        progress=lambda page, new, total: pages_seen.append((page, new, total)),
    )

    assert len(cards) == 3  # BMW, Audi, Mercedes; Audi repeats across pages
    assert pages_seen[0] == (0, 2, 2)
    assert pages_seen[1] == (1, 1, 3)
    assert pages_seen[2] == (2, 0, 3)


def test_collector_persists_to_storage(tmp_path):
    adb = FakeADB(pages=[SAMPLE_XML, SAMPLE_XML])
    collector = OLXCollector(adb=adb)
    storage = OLXStorage(tmp_path / "olx.sqlite")

    summary = collector.collect_to_storage(storage, query="лобове скло")

    assert summary == {"parsed": 2, "inserted": 2}
    assert storage.count() == 2


def test_collector_launch_search_deep_link():
    adb = FakeADB(pages=[])
    collector = OLXCollector(adb=adb)
    collector.launch_search("лобове скло")

    assert adb.commands
    assert "am start" in adb.commands[0]
    assert "q-" in adb.commands[0]
    assert collector.search_deep_link("лобове скло").startswith(
        "https://www.olx.ua/d/uk/list/q-"
    )


# --- OLXStorage -------------------------------------------------------------


def _sample_cards():
    return CardParser().parse(PAGE_TWO_XML, query="лобове скло") + CardParser().parse(
        SAMPLE_XML, query="лобове скло"
    )


def test_storage_roundtrip_and_deduplication(tmp_path):
    storage = OLXStorage(tmp_path / "olx.sqlite")
    cards = _sample_cards()

    # Audi card repeats on both pages — only 3 unique fingerprints.
    assert storage.save_ads(cards) == 3
    assert storage.save_ads(cards) == 0  # fingerprints already stored

    assert storage.count() == 3
    assert storage.count(query="лобове скло") == 3
    assert storage.count(query="інше") == 0

    fetched = storage.get_ads(query="лобове скло")
    assert len(fetched) == 3
    by_title = {card.title: card for card in fetched}
    mercedes = by_title["Лобове скло Mercedes W211 E-class"]
    assert mercedes.price == 5500.0
    assert mercedes.city == "Дніпро"
    assert mercedes.url is not None
    assert mercedes.raw_texts  # raw payload survives the roundtrip

    assert storage.queries() == ["лобове скло"]
    storage.close()


def test_storage_in_memory():
    with OLXStorage() as storage:
        card = AdCard(title="Тест", price=1.0, currency="UAH", city="Київ")
        assert storage.save_ads([card]) == 1
        assert storage.get_ads()[0].title == "Тест"


# --- Analytics & recommendations ------------------------------------------


def _market_ads():
    return [
        AdCard(
            title="Лобове скло BMW X3 з підігрівом",
            price=6000.0,
            currency="UAH",
            city="Київ",
            is_top=True,
        ),
        AdCard(
            title="Скло лобове BMW X3 оригінал",
            price=7000.0,
            currency="UAH",
            city="Львів",
        ),
        AdCard(
            title="Лобове скло BMW Х3 б/у",
            price=8000.0,
            currency="UAH",
            city="Дніпро",
            is_top=True,
        ),
        AdCard(title="Скло BMW X3", price=None, currency=None, city="Одеса"),
    ]


def test_competitor_analyzer_report():
    report = CompetitorAnalyzer().analyze(_market_ads(), query="лобове скло")

    assert report.total_ads == 4
    assert report.priced_ads == 3
    assert report.min_price == 6000.0
    assert report.max_price == 8000.0
    assert report.median_price == 7000.0
    assert report.top_share == 0.5
    assert dict(report.top_cities)["Київ"] == 1
    assert report.to_dict()["query"] == "лобове скло"


def test_competitor_price_percentile():
    analyzer = CompetitorAnalyzer()
    assert analyzer.price_percentile(_market_ads(), 6000.0) == round(1 / 3, 4)
    assert analyzer.price_percentile(_market_ads(), 8000.0) == 1.0
    assert analyzer.price_percentile([], 5000.0) is None


def test_recommendation_engine_advises_price_and_keywords():
    my_ad = AdCard(title="Лобове скло BMW X3", price=9000.0, currency="UAH")
    advice = RecommendationEngine().recommend(_market_ads(), my_ad=my_ad)

    assert advice.suggested_price == round(7000.0 * 0.97)
    assert advice.verdict == "above_market"
    assert advice.use_top_promotion is True
    assert advice.title_keywords  # market keywords missing from my title
    assert "bmw" not in advice.title_keywords  # already in my title
    text = advice.to_text()
    assert "Рекомендована ціна" in text


def test_recommendation_engine_below_market_and_empty_market():
    cheap = AdCard(title="Скло", price=1000.0, currency="UAH")
    advice = RecommendationEngine().recommend(_market_ads(), my_ad=cheap)
    assert advice.verdict == "below_market"

    empty = RecommendationEngine().recommend([], my_ad=None)
    assert empty.verdict == "unknown"
    assert empty.suggested_price is None
    assert empty.title_keywords == []
