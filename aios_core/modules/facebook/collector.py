"""Facebook Marketplace collector — ADB-driven product collection via Facebook app.

Facebook Marketplace is an OLX-like marketplace inside the Facebook app.
This collector scrolls through Marketplace search results, parses product
cards, and stores them for analysis.
"""

from __future__ import annotations

from pathlib import Path

from aios_core.modules.olx.adb import ADBController
from aios_core.modules.olx.card_parser import CardParser
from aios_core.modules.olx.models import AdCard


# Facebook Marketplace resource-id markers (from calibration)
CARD_RESOURCE_MARKERS = ("marketplace_item", "feed_item", "listing_card")


class FacebookCollector:
    """Dumps the visible UI, parses Marketplace product cards, swipes down.

    Reuses OLXCollector pattern with Facebook-specific card markers.
    """

    def __init__(
        self,
        adb: ADBController | None = None,
        parser: CardParser | None = None,
        max_swipes: int = 50,
        swipe_pause_s: float = 0.0,
        screen_width: int = 1080,
        screen_height: int = 2400,
    ) -> None:
        """Initialize FacebookCollector."""
        self.adb = adb or ADBController()
        self.parser = parser or CardParser()
        self.max_swipes = max_swipes
        self.swipe_pause_s = swipe_pause_s
        self.screen_width = screen_width
        self.screen_height = screen_height

    @staticmethod
    def search_deep_link(query: str) -> str:
        """Generate a fb://marketplace/search deep link."""
        return f"fb://marketplace/search?q={query}"

    def launch_search(self, query: str) -> dict:
        """Open Facebook and navigate to Marketplace search."""
        self.adb.open_app()
        self.adb.run(f"am start -a android.intent.action.VIEW -d '{self.search_deep_link(query)}'")
        return {"code": 0, "action": "marketplace_search", "query": query}

    def collect(
        self,
        query: str | None = None,
        max_cards: int = 50,
        filename: str = "screen.xml",
    ) -> list[AdCard]:
        """Collect Marketplace product cards by scrolling."""
        all_cards: list[AdCard] = []
        seen_urls: set[str] = set()
        empty_streak = 0

        for swipe_num in range(self.max_swipes):
            if len(all_cards) >= max_cards:
                break

            self.adb.dump_ui(filename)
            xml_text = Path(filename).read_text(encoding="utf-8") if Path(filename).exists() else ""

            new_cards = self.parser.parse(xml_text, query=query)
            added = 0
            for card in new_cards:
                if card.url not in seen_urls:
                    seen_urls.add(card.url)
                    all_cards.append(card)
                    added += 1

            if added == 0:
                empty_streak += 1
                if empty_streak >= 2:
                    break
            else:
                empty_streak = 0

            self.adb.swipe(
                self.screen_width // 2,
                self.screen_height * 3 // 4,
                self.screen_width // 2,
                self.screen_height // 4,
            )
            if self.swipe_pause_s > 0:
                import time
                time.sleep(self.swipe_pause_s)

        return all_cards

    def collect_to_storage(self, storage, query: str | None = None, max_cards: int = 50) -> dict:
        """Collect cards and save to storage."""
        cards = self.collect(query=query, max_cards=max_cards)
        storage.save_ads(cards)
        return {
            "collected": len(cards),
            "new": len(cards),
            "cards": [{"title": c.title, "price": c.price, "url": c.url} for c in cards],
        }
