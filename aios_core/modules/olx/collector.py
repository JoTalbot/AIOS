"""AIOS OLX Android Agent — automated scrolling card collection via ADB."""

from __future__ import annotations

import tempfile
import time
from pathlib import Path
from typing import Callable, Dict, List, Optional
from urllib.parse import quote

from .adb import ADBController
from .card_parser import CardParser
from .models import AdCard


class OLXCollector:
    """Dumps the visible UI, parses cards, swipes down, repeats.

    Collection stops when ``max_cards`` is reached, when two consecutive
    screens yield no new cards (end of the feed), or when ``max_swipes``
    is exhausted. Any ADB-like object implementing ``dump_ui``/``swipe``/``run``
    can be injected, which keeps the collector fully testable off-device.
    """

    def __init__(
        self,
        adb: Optional[ADBController] = None,
        parser: Optional[CardParser] = None,
        max_swipes: int = 50,
        swipe_pause_s: float = 0.0,
        screen_width: int = 1080,
        screen_height: int = 2400,
    ):
        self.adb = adb or ADBController()
        self.parser = parser or CardParser()
        self.max_swipes = max_swipes
        self.swipe_pause_s = swipe_pause_s
        self.screen_width = screen_width
        self.screen_height = screen_height

    @staticmethod
    def search_deep_link(query: str) -> str:
        """OLX search URL that deep-links into the Android app."""
        slug = quote("-".join(query.lower().split()))
        return f"https://www.olx.ua/d/uk/list/q-{slug}/"

    def launch_search(self, query: str) -> Dict[str, object]:
        """Open the OLX app directly on the results screen for ``query``."""
        link = self.search_deep_link(query)
        return self.adb.run(
            f'adb shell am start -a android.intent.action.VIEW -d "{link}"'
        )

    def collect(
        self,
        query: Optional[str] = None,
        max_cards: int = 100,
        progress: Optional[Callable[[int, int, int], None]] = None,
    ) -> List[AdCard]:
        """Scroll the results feed and collect deduplicated cards.

        Args:
            query: Search query tag stored on every collected card.
            max_cards: Stop after collecting this many unique cards.
            progress: Optional callback ``(page, new_cards, total_cards)``.

        Returns:
            Deduplicated list of collected cards in discovery order.
        """
        seen = set()
        collected: List[AdCard] = []
        idle_pages = 0

        with tempfile.TemporaryDirectory(prefix="aios_olx_") as tmp_dir:
            dump_path = Path(tmp_dir) / "screen.xml"
            for page in range(self.max_swipes + 1):
                self.adb.dump_ui(str(dump_path))
                if not dump_path.exists():
                    break
                page_cards = self.parser.parse(dump_path, query=query)
                dump_path.unlink(missing_ok=True)

                new_cards = []
                for card in page_cards:
                    if card.fingerprint not in seen:
                        seen.add(card.fingerprint)
                        new_cards.append(card)
                collected.extend(new_cards)

                if progress is not None:
                    progress(page, len(new_cards), len(collected))
                if len(collected) >= max_cards:
                    break
                if not new_cards:
                    idle_pages += 1
                    if idle_pages >= 2:
                        break
                else:
                    idle_pages = 0

                self._swipe_feed()
                if self.swipe_pause_s:
                    time.sleep(self.swipe_pause_s)

        return collected[:max_cards]

    def collect_to_storage(
        self,
        storage,
        query: Optional[str] = None,
        max_cards: int = 100,
        progress: Optional[Callable[[int, int, int], None]] = None,
    ) -> Dict[str, int]:
        """Collect cards, persist them and sync feed activity.

        Ads of ``query`` missing from the collected feed are marked inactive
        (likely sold/removed); the summary reports how many changed state.
        """
        cards = self.collect(query=query, max_cards=max_cards, progress=progress)
        inserted = storage.save_ads(cards)
        summary = {"parsed": len(cards), "inserted": inserted}
        if query is not None:
            summary["deactivated"] = storage.sync_activity(
                query, [card.fingerprint for card in cards]
            )
        return summary

    def _swipe_feed(self) -> None:
        """Swipe up over the central part of the feed to load new cards."""
        x = self.screen_width // 2
        y_from = int(self.screen_height * 0.8)
        y_to = int(self.screen_height * 0.2)
        self.adb.swipe(x, y_from, x, y_to, duration=400)
