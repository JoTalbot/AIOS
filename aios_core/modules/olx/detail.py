"""AIOS OLX Android Agent — detail page parsing (full ad view)."""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Union

from .text_utils import normalize_text, parse_price, parse_published

_AD_ID_RE = re.compile(r"ID([A-Za-z0-9]{4,})\.html")
_VIEWS_RE = re.compile(r"(?:переглядів|просмотров|views?)\s*:?\s*(\d+)", re.IGNORECASE)
_PARAM_RE = re.compile(r"^([А-Яа-яІіЇїЄєҐґA-Za-z' -]{2,30}):\s+(.+)$")
_SELLER_SINCE_RE = re.compile(
    r"(?:на OLX з|на OLX с)\s+(.+)", re.IGNORECASE
)
_PRIVATE_MARKERS = ("приватн", "частн")
_BUSINESS_MARKERS = ("бізнес", "business")


@dataclass
class AdDetail:
    """Full ad page data parsed from the open listing screen."""

    title: str
    price: Optional[float] = None
    currency: Optional[str] = None
    description: str = ""
    params: Dict[str, str] = field(default_factory=dict)
    seller_name: Optional[str] = None
    seller_type: Optional[str] = None  # "private" | "business"
    seller_since: Optional[str] = None
    city: Optional[str] = None
    views_count: Optional[int] = None
    published_text: Optional[str] = None
    published_at: Optional[str] = None
    ad_id: Optional[str] = None
    url: Optional[str] = None
    raw_texts: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, object]:
        return {
            "title": self.title,
            "price": self.price,
            "currency": self.currency,
            "description": self.description,
            "params": dict(self.params),
            "seller_name": self.seller_name,
            "seller_type": self.seller_type,
            "seller_since": self.seller_since,
            "city": self.city,
            "views_count": self.views_count,
            "published_text": self.published_text,
            "published_at": self.published_at,
            "ad_id": self.ad_id,
            "url": self.url,
        }


class AdDetailParser:
    """Parses the open ad screen into an :class:`AdDetail`."""

    def parse(
        self, xml_source: Union[str, Path, ET.Element], url: Optional[str] = None
    ) -> AdDetail:
        if isinstance(xml_source, ET.Element):
            root = xml_source
        else:
            text_or_path = str(xml_source)
            if text_or_path.lstrip().startswith("<"):
                root = ET.fromstring(text_or_path)
            else:
                root = ET.parse(text_or_path).getroot()

        texts: List[str] = []
        ad_id: Optional[str] = None
        found_url: Optional[str] = url
        title: str = ""
        description: str = ""

        for node in root.iter("node"):
            resource_id = (node.attrib.get("resource-id") or "").lower()
            text = normalize_text(node.attrib.get("text"))
            if text:
                texts.append(text)
                if "adtitle" in resource_id and not title:
                    title = text
                if "description" in resource_id and len(text) > len(description):
                    description = text
            for value in node.attrib.values():
                if ad_id is None:
                    match = _AD_ID_RE.search(value)
                    if match:
                        ad_id = match.group(1)

        detail = self.detail_from_texts(texts)
        if title:
            detail.title = title
        if description:
            detail.description = description
        detail.ad_id = ad_id
        detail.url = found_url
        return detail

    @staticmethod
    def detail_from_texts(texts: List[str]) -> AdDetail:
        """Classify an ordered text list into an :class:`AdDetail`.

        Text-only fallback for Compose screens without resource-ids:
        price/date/seller/views are recognised by shape, ``key: value``
        lines become params, the longest remaining block is the description
        and the first meaningful line is the title.
        """
        detail = AdDetail(title="", raw_texts=list(texts))
        leftovers: List[str] = []
        expect_seller_name = False

        for raw in texts:
            lowered = raw.lower()
            if detail.price is None:
                parsed_price = parse_price(raw)
                if parsed_price is not None:
                    detail.price, detail.currency = parsed_price
                    continue
            if detail.published_at is None:
                parsed_date = parse_published(raw)
                if parsed_date is not None:
                    detail.published_text = normalize_text(raw)
                    detail.published_at = parsed_date
                    continue
            views = _VIEWS_RE.search(raw)
            if views and detail.views_count is None:
                detail.views_count = int(views.group(1))
                continue
            since = _SELLER_SINCE_RE.search(raw)
            if since and detail.seller_since is None:
                detail.seller_since = normalize_text(since.group(1))
                continue
            if any(marker in lowered for marker in _PRIVATE_MARKERS):
                detail.seller_type = "private"
                expect_seller_name = True
                continue
            if any(marker in lowered for marker in _BUSINESS_MARKERS):
                detail.seller_type = "business"
                expect_seller_name = True
                continue
            # The seller name line immediately follows the seller-type marker.
            if expect_seller_name and 2 <= len(raw) <= 40:
                detail.seller_name = raw
                expect_seller_name = False
                continue
            param = _PARAM_RE.match(raw)
            if param and len(raw) < 80:
                key = normalize_text(param.group(1))
                if key.lower() not in {"стан", "состояние"} or "стан" not in detail.params:
                    detail.params[key] = normalize_text(param.group(2))
                continue
            leftovers.append(raw)

        # Description: the longest non-trivial leftover.
        if leftovers:
            longest = max(leftovers, key=len)
            if len(longest) >= 40:
                detail.description = longest
                leftovers.remove(longest)

        if leftovers:
            detail.title = leftovers[0]
        if len(leftovers) > 1 and detail.city is None:
            candidate = leftovers[1]
            if len(candidate) <= 40:
                detail.city = candidate
        return detail
