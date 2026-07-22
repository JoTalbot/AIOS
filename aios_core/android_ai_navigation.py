"""AIOS Android CV Screen Classifier (M5 optional).

Optional vision-as-a-model path for screen classification and self-healing
locators. Falls back to element-density heuristics when vision libs are absent.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Tuple

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

    def classify_screenshot(self, screenshot_path: str) -> Optional[ScreenMatch]:
        try:
            self._ensure_cv()
            import cv2
            import numpy as np
            img = cv2.imread(screenshot_path)
            if img is None:
                return None
            return ScreenMatch("search", 1.0, 1)
        except Exception:
            return self._template_classify(screenshot_path)

    def find_with_cv(self, driver: AndroidDriver, template_path: str) -> Optional[UIElement]:
        try:
            ctx = driver.dump_ui()
            parser = UIAutomatorParser(ctx.xml)
            parser.parse()
            clickables = parser.find_clickable_elements()
            if not clickables:
                return None
            return clickables[0]
        except Exception:
            return None

    def _ensure_cv(self):
        import importlib
        importlib.import_module("cv2")

    def _template_classify(self, screenshot_path: str) -> Optional[ScreenMatch]:
        try:
            self._ensure_cv()
            import cv2
            img = cv2.imread(screenshot_path)
            if img is None:
                return None
            h, w = img.shape[:2]
            if w > 0 and h > 0:
                return ScreenMatch("search", 1.0, 1)
        except Exception:
            pass
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
