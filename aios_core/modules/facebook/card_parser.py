"""Facebook Marketplace card parser — extracts product cards from UI dumps."""

from __future__ import annotations

from aios_core.modules.olx.card_parser import CardParser
from aios_core.modules.olx.models import AdCard

# Facebook-specific parsing markers
FB_CARD_RESOURCE_IDS = ("marketplace_item", "feed_item", "listing_card")
FB_TITLE_MARKERS = ("title", "description", "item_name")


class FacebookCardParser(CardParser):
    """Extended CardParser with Facebook Marketplace-specific card extraction."""

    def parse(self, xml: str, query: str | None = None) -> list[AdCard]:
        """Parse Facebook UI dump for Marketplace product cards."""
        cards = super().parse(xml, query=query)

        if xml:
            import re

            pattern = (
                r'<node[^>]*resource-id="[^"]*({})[^"]*"[^>]*text="([^"]*)"'.format(
                    "|".join(FB_CARD_RESOURCE_IDS)
                )
            )
            matches = re.findall(pattern, xml, re.IGNORECASE)

            for marker, text in matches:
                if text and text.strip():
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
                    if not any(c.title == card.title for c in cards):
                        cards.append(card)

        return cards

    def _extract_price(self, text: str) -> float | None:
        """Extract price from Facebook Marketplace text."""
        import re

        m = re.search(r"(\d[\d\s]+)\s*(грн|uah|\$|₴)", text.lower())
        if m:
            try:
                return float(m.group(1).replace(" ", ""))
            except ValueError:
                pass
        return None
