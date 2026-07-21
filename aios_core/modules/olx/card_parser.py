"""AIOS OLX Android Agent — listing card extraction from UIAutomator dumps."""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List, Optional, Union

from .models import AdCard
from .text_utils import (
    is_no_price_label,
    is_top_text,
    normalize_text,
    parse_price,
    parse_published,
)

# Jetpack Compose leaves most cards without resource-ids; known markers are
# matched as substrings so both "ua.slando:id/adListing_adGridCard" and short
# forms work.
CARD_RESOURCE_MARKERS = ("adlisting_adgridcard",)

_URL_RE = re.compile(r"https?://[^\s\"'<>]*olx\.[^\s\"'<>]+", re.IGNORECASE)
_AD_ID_RE = re.compile(r"ID([A-Za-z0-9]{4,})\.html")


class CardParser:
    """Turns UIAutomator XML dumps into structured :class:`AdCard` objects."""

    def parse(
        self,
        xml_source: Union[str, Path, ET.Element],
        query: Optional[str] = None,
    ) -> List[AdCard]:
        """Parse every listing card found in a UI dump.

        Args:
            xml_source: Path to the XML file, raw XML text or a root Element.
            query: Search query these cards belong to (stored on each card).

        Returns:
            List of cards that have at least a title.
        """
        if isinstance(xml_source, ET.Element):
            root = xml_source
        else:
            text_or_path = str(xml_source)
            if text_or_path.lstrip().startswith("<"):
                root = ET.fromstring(text_or_path)
            else:
                root = ET.parse(text_or_path).getroot()

        cards: List[AdCard] = []
        for node in root.iter("node"):
            resource_id = (node.attrib.get("resource-id") or "").lower()
            if any(marker in resource_id for marker in CARD_RESOURCE_MARKERS):
                card = self._card_from_node(node, query=query)
                if card.title:
                    cards.append(card)
        return cards

    def _card_from_node(self, node: ET.Element, query: Optional[str]) -> AdCard:
        texts: List[str] = []
        url: Optional[str] = None
        ad_id: Optional[str] = None

        for child in node.iter():
            text = normalize_text(child.attrib.get("text"))
            if text and not _URL_RE.match(text):
                texts.append(text)
            for value in child.attrib.values():
                if url is None:
                    url_match = _URL_RE.search(value)
                    if url_match:
                        url = url_match.group(0)
                id_match = _AD_ID_RE.search(value)
                if id_match:
                    ad_id = id_match.group(1)

        return self.card_from_texts(texts, query=query, url=url, ad_id=ad_id)

    @staticmethod
    def card_from_texts(
        texts: List[str],
        query: Optional[str] = None,
        url: Optional[str] = None,
        ad_id: Optional[str] = None,
    ) -> AdCard:
        """Classify an ordered list of card texts into an :class:`AdCard`.

        OLX card layout is: title, price, city, publication date, TOP badge —
        but the order is not guaranteed, so every text is classified by shape.
        The first unclassified text becomes the title, the second the city.
        """
        price: Optional[float] = None
        currency: Optional[str] = None
        published_text: Optional[str] = None
        published_at: Optional[str] = None
        is_top = False
        leftovers: List[str] = []

        for raw in texts:
            if is_no_price_label(raw):
                continue  # «Договірна» / «Обмін» — price stays None, text is dropped
            if price is None:
                parsed_price = parse_price(raw)
                if parsed_price is not None:
                    price, currency = parsed_price
                    continue
            if published_at is None:
                parsed_date = parse_published(raw)
                if parsed_date is not None:
                    published_text = normalize_text(raw)
                    published_at = parsed_date
                    continue
            if is_top_text(raw):
                is_top = True
                continue
            if raw not in leftovers:
                leftovers.append(raw)

        title = leftovers[0] if leftovers else ""
        city = leftovers[1] if len(leftovers) > 1 else None

        return AdCard(
            title=title,
            price=price,
            currency=currency,
            city=city,
            published_text=published_text,
            published_at=published_at,
            is_top=is_top,
            ad_id=ad_id,
            url=url,
            query=query,
            raw_texts=list(texts),
        )
