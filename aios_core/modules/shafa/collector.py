"""Shafa.ua collector — ADB-driven product collection."""

from __future__ import annotations

from pathlib import Path
from aios_core.modules.olx.adb import ADBController
from aios_core.modules.olx.card_parser import CardParser
from aios_core.modules.olx.models import AdCard

PACKAGE = "com.shafa"


class ShafaCollector:
    """Dumps visible UI, parses product cards, swipes down.""" 

    def __init__(self, adb=None, parser=None, max_swipes=50, swipe_pause_s=0.0,
                 screen_width=1080, screen_height=2400) -> None:
        """Initialize ShafaCollector.""" 
        self.adb = adb or ADBController()
        self.parser = parser or CardParser()
        self.max_swipes = max_swipes
        self.swipe_pause_s = swipe_pause_s
        self.screen_width = screen_width
        self.screen_height = screen_height

    @staticmethod
    def search_deep_link(query: str) -> str:
        """Generate a shafa://search deep link.""" 
        return f"shafa://search?q={query}"

    def launch_search(self, query: str) -> dict:
        """Open Shafa app and navigate to search.""" 
        self.adb.open_app()
        self.adb.run(f"am start -a android.intent.action.VIEW -d '{self.search_deep_link(query)}'")
        return {"code": 0, "action": "search", "query": query}

    def collect(self, query=None, max_cards=50, filename="screen.xml") -> list[AdCard]:
        """Collect product cards by scrolling.""" 
        all_cards: list[AdCard] = []
        seen_urls: set[str] = set()
        empty_streak = 0
        for _ in range(self.max_swipes):
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
            self.adb.swipe(self.screen_width // 2, self.screen_height * 3 // 4,
                          self.screen_width // 2, self.screen_height // 4)
            if self.swipe_pause_s > 0:
                import time
                time.sleep(self.swipe_pause_s)
        return all_cards

    def collect_to_storage(self, storage, query=None, max_cards=50) -> dict:
        """Collect cards and save to storage.""" 
        cards = self.collect(query=query, max_cards=max_cards)
        storage.save_ads(cards)
        return {"collected": len(cards), "new": len(cards),
                "cards": [{"title": c.title, "price": c.price, "url": c.url} for c in cards]}
