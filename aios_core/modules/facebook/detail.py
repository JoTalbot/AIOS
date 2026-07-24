"""Facebook Marketplace detail parser — extracts product details from listing pages."""

from __future__ import annotations

from aios_core.modules.olx.detail import AdDetailParser


class FacebookDetailParser(AdDetailParser):
    """Extended AdDetailParser with Facebook Marketplace-specific detail extraction."""

    def parse_detail(self, xml: str) -> dict[str, object]:
        """Parse a Facebook Marketplace listing detail page."""
        if not xml:
            return {}

        import re

        result = {"description": "", "price": None, "seller": None, "location": None}

        # Extract text nodes
        text_pattern = r'<node[^>]*text="([^"]+)"[^>]*>'
        texts = re.findall(text_pattern, xml)

        if texts:
            result["description"] = max(texts, key=len).strip()[:500]

        # Extract price
        for text in texts:
            m = re.search(r"(\d[\d\s]+)\s*(грн|uah|\$|₴)", text.lower())
            if m:
                try:
                    result["price"] = float(m.group(1).replace(" ", ""))
                except ValueError:
                    pass

        # Extract seller name
        seller_pattern = r'<node[^>]*resource-id="[^"]*seller[^"]*"[^>]*text="([^"]*)"'
        seller_match = re.search(seller_pattern, xml, re.IGNORECASE)
        if seller_match:
            result["seller"] = seller_match.group(1)

        # Extract location
        loc_pattern = r'<node[^>]*resource-id="[^"]*location[^"]*"[^>]*text="([^"]*)"'
        loc_match = re.search(loc_pattern, xml, re.IGNORECASE)
        if loc_match:
            result["location"] = loc_match.group(1)

        return result
