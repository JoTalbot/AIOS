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
        pacer=None,
    ):
        self.adb = adb or ADBController()
        self.parser = parser or CardParser()
        self.max_swipes = max_swipes
        self.swipe_pause_s = swipe_pause_s
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.pacer = pacer

    @staticmethod
    def search_deep_link(
        query: str,
        min_price: float | None = None,
        max_price: float | None = None,
        sort: str | None = None,
    ) -> str:
        """OLX search URL with optional filters, deep-linking into the app.

        Args:
            query: Search text.
            min_price/max_price: Price range filter (UAH).
            sort: ``created_at:desc`` (newest first), ``filter_float_price:asc``
                or ``filter_float_price:desc``.
        """
        slug = quote("-".join(query.lower().split()))
        url = f"https://www.olx.ua/d/uk/list/q-{slug}/"
        params = []
        if min_price is not None:
            params.append(f"search%5Bfilter_float_price%3Afrom%5D={min_price:g}")
        if max_price is not None:
            params.append(f"search%5Bfilter_float_price%3Ato%5D={max_price:g}")
        if sort:
            params.append(f"search%5Border%5D={quote(sort)}")
        if params:
            url += "?" + "&".join(params)
        return url

    def launch_search(
        self,
        query: str,
        min_price: float | None = None,
        max_price: float | None = None,
        sort: str | None = None,
    ) -> Dict[str, object]:
        """Open the OLX app on the (optionally filtered) results screen."""
        link = self.search_deep_link(query, min_price, max_price, sort)
        return self.adb.run(f'adb shell am start -a android.intent.action.VIEW -d "{link}"')

    def collect(
        self,
        query: str | None = None,
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

                if self.pacer is not None and not self.pacer.before_action():
                    break  # pacing-лимит — честный стоп, не обход
                self._swipe_feed()
                if self.swipe_pause_s:
                    time.sleep(self.swipe_pause_s)

        return collected[:max_cards]

    def collect_to_storage(
        self,
        storage,
        query: str | None = None,
        max_cards: int = 100,
        progress: Optional[Callable[[int, int, int], None]] = None,
    ) -> dict[str, int]:
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
