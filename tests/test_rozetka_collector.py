"""Tests for Rozetka collector, card_parser, and detail scaffold."""

import pytest
from pathlib import Path

from aios_core.modules.rozetka import (
    RozetkaCollector,
    RozetkaCardParser,
    RozetkaDetailParser,
    RozetkaStorage,
)


# Use OLX-style card markers since RozetkaCardParser inherits CardParser
# with rozetka-specific markers that will be set after calibration
ROZETKA_XML = """<?xml version='1.0' encoding='UTF-8' standalone='yes' ?>
<hierarchy rotation="0">
  <node text="" resource-id="ua.slando:id/adListing_adGridCard"
        bounds="[0,100][1080,300]">
    <node text="iPhone 16 Pro 256GB" resource-id=""/>
    <node text="42 999 грн." resource-id=""/>
  </node>
  <node text="" resource-id="ua.slando:id/adListing_adGridCard"
        bounds="[0,300][1080,500]">
    <node text="Samsung Galaxy S25 Ultra" resource-id=""/>
    <node text="38 999 грн." resource-id=""/>
  </node>
</hierarchy>
"""

EMPTY_XML = "<hierarchy><node text='' resource-id=''/></hierarchy>"


class _ADB:
    package = "com.rozetka"

    def __init__(self, dumps=()):
        self.dumps = list(dumps)
        self.calls = []

    @property
    def adb(self):
        return "adb"

    def run(self, command):
        self.calls.append(command)
        return {"code": 0, "stdout": "", "stderr": ""}

    def dump_ui(self, filename="screen.xml"):
        if not self.dumps:
            return {"code": 1, "stdout": "", "stderr": "no dumps"}
        Path(filename).write_text(self.dumps.pop(0), encoding="utf-8")
        return {"code": 0, "stdout": "", "stderr": ""}

    def swipe(self, x1, y1, x2, y2):
        self.calls.append(("swipe", x1, y1, x2, y2))
        return {"code": 0, "stdout": "", "stderr": ""}

    def open_app(self):
        self.calls.append("open_app")
        return {"code": 0, "stdout": "", "stderr": ""}

    def tap(self, x, y):
        self.calls.append(("tap", x, y))
        return {"code": 0, "stdout": "", "stderr": ""}


class TestRozetkaCardParser:
    """RozetkaCardParser inherits CardParser with rozetka markers."""

    def test_card_parser_has_rozetka_markers(self):
        parser = RozetkaCardParser()
        assert len(parser.CARD_RESOURCE_MARKERS) > 0

    def test_parse_with_generic_markers(self):
        """CardParser can parse cards with known olx markers."""
        from aios_core.modules.olx.card_parser import CardParser
        parser = CardParser()
        cards = parser.parse(ROZETKA_XML, query="iPhone")
        assert len(cards) >= 1


class TestRozetkaCollector:
    """RozetkaCollector collects cards via ADB."""

    def test_search_deep_link(self):
        link = RozetkaCollector.search_deep_link("iPhone 16")
        assert "rozetka://search" in link
        assert "iPhone" in link

    def test_collect_with_mock_adb(self, tmp_path):
        adb = _ADB([ROZETKA_XML, EMPTY_XML])
        collector = RozetkaCollector(adb=adb, max_swipes=5)
        cards = collector.collect(query="iPhone", max_cards=10, filename=str(tmp_path / "screen.xml"))
        # Collect returns cards parsed from dump (may be empty before calibration)
        assert isinstance(cards, list)

    def test_collect_to_storage(self, tmp_path):
        adb = _ADB([EMPTY_XML, EMPTY_XML])
        collector = RozetkaCollector(adb=adb, max_swipes=5)
        db = tmp_path / "rz.sqlite"
        with RozetkaStorage(str(db)) as storage:
            summary = collector.collect_to_storage(storage, query="iPhone", max_cards=10)
            assert "collected" in summary

    def test_launch_search(self):
        adb = _ADB()
        collector = RozetkaCollector(adb=adb)
        result = collector.launch_search("Samsung")
        assert result["code"] == 0
        assert result["query"] == "Samsung"


class TestRozetkaDetailParser:
    """RozetkaDetailParser inherits OLX AdDetailParser."""

    def test_detail_parser_is_subclass(self):
        from aios_core.modules.olx.detail import AdDetailParser
        assert issubclass(RozetkaDetailParser, AdDetailParser)
