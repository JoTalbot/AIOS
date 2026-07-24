"""TikTok detail parser — extracts product detail from video/product pages."""

from __future__ import annotations

from dataclasses import dataclass, field

from aios_core.modules.olx.detail import AdDetailParser


@dataclass
class TikTokVideoDetail:
    """Detailed information about a TikTok video/product listing."""

    title: str = ""
    description: str = ""
    price: float | None = None
    currency: str | None = None
    product_link: str | None = None
    creator: str | None = None
    likes: int = 0
    comments: int = 0
    shares: int = 0
    hashtags: list[str] = field(default_factory=list)
    product_tags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        """Serialize to dict."""
        return {
            "title": self.title,
            "description": self.description,
            "price": self.price,
            "currency": self.currency,
            "product_link": self.product_link,
            "creator": self.creator,
            "likes": self.likes,
            "comments": self.comments,
            "shares": self.shares,
            "hashtags": self.hashtags,
            "product_tags": self.product_tags,
        }


class TikTokDetailParser(AdDetailParser):
    """Extended AdDetailParser with TikTok-specific video/product detail extraction.

    Parses video description, product tags, hashtags, and engagement metrics.
    """

    def parse_detail(self, xml: str) -> TikTokVideoDetail:
        """Parse a TikTok video/product detail page from UI dump.

        Args:
            xml: UIAutomator XML dump of the detail page.

        Returns:
            TikTokVideoDetail with extracted information.
        """
        detail = TikTokVideoDetail()

        if not xml:
            return detail

        import re

        # Extract description text
        desc_pattern = r'<node[^>]*text="([^"]+)"[^>]*bounds="[^"]*"[^>]*>'
        texts = re.findall(desc_pattern, xml)

        # Find longest text as description
        if texts:
            longest = max(texts, key=len)
            detail.description = longest.strip()[:500]
            detail.title = longest.strip()[:100]

        # Extract price
        detail.price = self._extract_price(xml)

        # Extract hashtags
        hashtag_pattern = r'#(\w+)'
        for text in texts:
            tags = re.findall(hashtag_pattern, text)
            detail.hashtags.extend(tags)

        # Extract product tags
        product_pattern = r'<node[^>]*resource-id="[^"]*product[^"]*"[^>]*text="([^"]*)"'
        product_texts = re.findall(product_pattern, xml, re.IGNORECASE)
        detail.product_tags = product_texts

        # Extract creator name
        creator_pattern = r'<node[^>]*resource-id="[^"]*author[^"]*"[^>]*text="([^"]*)"'
        creator_match = re.search(creator_pattern, xml, re.IGNORECASE)
        if creator_match:
            detail.creator = creator_match.group(1)

        # Extract engagement numbers
        for text in texts:
            m = re.search(r'(\d[\d\s]*)\s*(likes|лайків)', text.lower())
            if m:
                try:
                    detail.likes = int(m.group(1).replace(" ", ""))
                except ValueError:
                    pass
            m = re.search(r'(\d[\d\s]*)\s*(comments|комент)', text.lower())
            if m:
                try:
                    detail.comments = int(m.group(1).replace(" ", ""))
                except ValueError:
                    pass

        return detail

    def _extract_price(self, xml: str) -> float | None:
        """Extract price from TikTok detail page."""
        import re

        price_pattern = r'(\d[\d\s]+)\s*(грн|uah|\$|₴)'
        m = re.search(price_pattern, xml.lower())
        if m:
            try:
                return float(m.group(1).replace(" ", ""))
            except ValueError:
                pass
        return None
