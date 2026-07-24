"""TikTok card parser — extracts product/video cards from UI dumps."""

from __future__ import annotations

from aios_core.modules.olx.card_parser import CardParser
from aios_core.modules.olx.models import AdCard


# TikTok-specific parsing markers
TIKTOK_CARD_RESOURCE_IDS = ("video_card", "product_card", "tiktok_card")
TIKTOK_TITLE_MARKERS = ("desc", "description", "title", "caption")
TIKTOK_PRICE_MARKERS = ("price", "uah", "грн", "$")


class TikTokCardParser(CardParser):
    """Extended CardParser with TikTok-specific video/product card extraction.

    Inherits base CardParser logic for generic XML parsing.
    Adds TikTok-specific resource-id and text pattern matching.
    """

    def parse(self, xml: str, query: str | None = None) -> list[AdCard]:
        """Parse TikTok UI dump for product/video cards.

        Args:
            xml: UIAutomator XML dump.
            query: Search query for context.

        Returns:
            List of AdCard objects extracted from the dump.
        """
        # First try standard CardParser
        cards = super().parse(xml, query=query)

        # Add TikTok-specific card extraction
        if xml:
            import re

            # Find video/product card nodes
            pattern = r'<node[^>]*resource-id="[^"]*({})[^"]*"[^>]*text="([^"]*)"'.format(
                "|".join(TIKTOK_CARD_RESOURCE_IDS)
            )
            matches = re.findall(pattern, xml, re.IGNORECASE)

            for marker, text in matches:
                if text and text.strip():
                    # Extract price if present
                    price = self._extract_price(text)
                    card = AdCard(
                        title=text.strip()[:200],
                        price=price,
                        currency="UAH" if price else None,
                        city=None,
                        published_text=None,
                        is_top=False,
                        url=None,
                        ad_id=None,
                        query=query,
                        raw_texts=[text.strip()],
                    )
                    # Avoid duplicates from base parser
                    if not any(c.title == card.title for c in cards):
                        cards.append(card)

        return cards

    def _extract_price(self, text: str) -> float | None:
        """Try to extract a price from TikTok description text."""
        import re

        # Price patterns: "3000 грн", "3 000 UAH", "$50"
        m = re.search(r'(\d[\d\s]+)\s*(грн|uah|\$)', text.lower())
        if m:
            try:
                return float(m.group(1).replace(" ", ""))
            except ValueError:
                pass

        m = re.search(r'\b(\d{3,6})\b', text)
        if m:
            try:
                return float(m.group(1))
            except ValueError:
                pass

        return None
