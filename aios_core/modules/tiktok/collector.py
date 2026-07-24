"""TikTok collector — ADB-driven video content collection for product discovery.

TikTok is a video-first platform: products appear as video cards in
search results and feed. This collector scrolls through search results,
dumps UI, parses video cards, and stores them for analysis.

Unlike OLX/Rozetka card-based platforms, TikTok collection focuses on:
- Video card extraction (thumbnail + description + link)
- Product tag detection (items tagged in videos)
- Creator/seller profile extraction
"""

from __future__ import annotations

from pathlib import Path

from aios_core.modules.olx.adb import ADBController
from aios_core.modules.olx.card_parser import CardParser
from aios_core.modules.olx.models import AdCard

# TikTok resource-id markers (from calibration)
CARD_RESOURCE_MARKERS = ("video_card", "product_card", "tiktok_card", "item_card")
PRODUCT_TAG_MARKERS = ("product_tag", "shop_tag", "buy_now")


class TikTokCollector:
    """Dumps the visible UI, parses video/product cards, swipes down, repeats.

    Reuses OLXCollector pattern with TikTok-specific card markers.
    Collection stops when max_cards is reached or two consecutive
    screens yield no new cards.
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
        """Initialize TikTokCollector."""
        self.adb = adb or ADBController()
        self.parser = parser or CardParser()
        self.max_swipes = max_swipes
        self.swipe_pause_s = swipe_pause_s
        self.screen_width = screen_width
        self.screen_height = screen_height

    @staticmethod
    def search_deep_link(query: str) -> str:
        """Generate a tiktok://search deep link."""
        return f"tiktok://search?q={query}"

    def launch_search(self, query: str) -> dict:
        """Open the TikTok app and navigate to search results."""
        self.adb.open_app()
        self.adb.run(
            f"am start -a android.intent.action.VIEW -d '{self.search_deep_link(query)}'"
        )
        return {"code": 0, "action": "search", "query": query}

    def collect(
        self,
        query: str | None = None,
        max_cards: int = 50,
        filename: str = "screen.xml",
    ) -> list[AdCard]:
        """Collect product/video cards by scrolling through search results.

        Returns a list of AdCard objects parsed from the UI dumps.
        """
        all_cards: list[AdCard] = []
        seen_urls: set[str] = set()
        empty_streak = 0

        for swipe_num in range(self.max_swipes):
            if len(all_cards) >= max_cards:
                break

            self.adb.dump_ui(filename)
            xml_text = (
                Path(filename).read_text(encoding="utf-8")
                if Path(filename).exists()
                else ""
            )

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

            # Swipe down to next page
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

    def collect_to_storage(
        self, storage, query: str | None = None, max_cards: int = 50
    ) -> dict:
        """Collect cards and save to storage.

        Returns a summary dict with count and cards.
        """
        cards = self.collect(query=query, max_cards=max_cards)
        storage.save_ads(cards)
        return {
            "collected": len(cards),
            "new": len(cards),
            "cards": [
                {"title": c.title, "price": c.price, "url": c.url} for c in cards
            ],
        }
