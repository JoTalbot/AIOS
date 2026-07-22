"""AIOS Android AI-Powered UI Navigation (M5).

Lightweight self-healing locators and screen classification grounded on the
existing UIAutomator parser. Uses simple similarity heuristics and optional
multidimensional world model hooks.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from aios_core.android_parser import UIAutomatorParser, UIElement
from aios_core.android_driver import AndroidDriver


@dataclass
class ScreenMatch:
    screen_name: str
    score: float
    matched_elements: int


class AIScreenClassifier:
    def __init__(self):
        self.parser = UIAutomatorParser("")

    def classify(self, xml: str) -> Optional[ScreenMatch]:
        self.parser = UIAutomatorParser(xml)
        if not self.parser.parse():
            return None

        search_field = self.parser.find_search_field()
        results = self.parser.find_search_results()
        details = self.parser.find_item_details()

        candidates = [
            ScreenMatch("search", max(1, len(results)) * 2 + (1 if search_field else 0), len(results) + (1 if search_field else 0)),
            ScreenMatch("item_details", 3, 1 if details else 0),
        ]

        best = max(candidates, key=lambda item: item.score)
        if best.matched_elements > 0:
            return best
        return None


class SelfHealingLocator:
    def __init__(self, driver: AndroidDriver):
        self.driver = driver
        self.parser = UIAutomatorParser("")

    def find(self, hints: List[str]) -> Optional[UIElement]:
        ctx = self.driver.dump_ui()
        self.parser = UIAutomatorParser(ctx.xml)
        if not self.parser.parse():
            return None
        for hint in hints:
            elems = self.parser.find_elements_by_text(hint, partial=True)
            if elems:
                return elems[0]
            elems = self.parser.find_elements_by_resource(hint)
            if elems:
                return elems[0]
        return None

    def tap_hint(self, hints: List[str]) -> bool:
        elem = self.find(hints)
        if elem is None:
            return False
        x, y, _ = elem.center
        self.driver.tap(x, y)
        return True
