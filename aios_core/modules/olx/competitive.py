"""AIOS OLX Android Agent — competitor surveillance driven by own listings.

Derives a market query from each own listing, links similar market ads to it
(`olx_competitor_links`), and reports the competitive position of every own
ad: who's cheaper, who's new in the niche, and where you rank by price.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

from .analytics import _tokenize
from .card_parser import CardParser
from .models import AdCard
from .own_ads import OwnAd

_SIMILARITY_THRESHOLD = 0.30

# Headings shown above the "other ads by this seller" block on an OLX
# detail page (Ukrainian and Russian app locales).
SELLER_SECTION_MARKERS = (
    "інші оголошення",
    "другие объявления",
    "другие предложения",
    "інші пропозиції",
)


def derive_query(title: str, max_tokens: int = 3) -> str:
    """Best search query for a listing title (top content tokens)."""
    tokens = _tokenize(title)
    return " ".join(tokens[:max_tokens])


def title_similarity(a: str, b: str) -> float:
    """Jaccard similarity over title token sets."""
    tokens_a = set(_tokenize(a))
    tokens_b = set(_tokenize(b))
    if not tokens_a or not tokens_b:
        return 0.0
    return len(tokens_a & tokens_b) / len(tokens_a | tokens_b)


def link_score(own: OwnAd, candidate: AdCard) -> float:
    """Combined similarity: title Jaccard + price proximity + city bonus."""
    title_sim = title_similarity(own.title, candidate.title or "")
    score = title_sim
    if own.price and candidate.price:
        ratio = min(own.price, candidate.price) / max(own.price, candidate.price)
        score += 0.15 * ratio
        # Competing means roughly the same market segment, not identical price.
    if own.price and candidate.price:
        if ratio >= 0.5:
            score += 0.10
    if candidate.city:
        score += 0.05
    return min(score, 1.0)


def _has_seller_section(root: ET.Element) -> bool:
    """True when the dump contains the "other ads by this seller" heading."""
    for node in root.iter("node"):
        raw = (node.attrib.get("text") or "").strip().lower()
        if raw and any(marker in raw for marker in SELLER_SECTION_MARKERS):
            return True
    return False


def parse_seller_ads(
    xml_source: Union[str, Path, ET.Element],
    query: Optional[str] = None,
    exclude_urls: Tuple[str, ...] = (),
    exclude_ad_ids: Tuple[str, ...] = (),
) -> List[AdCard]:
    """Parse the seller's other listings from an ad detail page dump.

    The OLX detail screen embeds a horizontal "other ads by this seller"
    block whose cards reuse the regular search-card layout, so this simply
    reuses :class:`CardParser` and applies two safety guards:

    * the dump must actually contain the seller-section heading
      (``SELLER_SECTION_MARKERS``) — otherwise an empty list is returned;
    * the ad currently being viewed is excluded by URL / ad-id.

    Args:
        xml_source: Path to the XML file, raw XML text or a root Element.
        query: Query tag stored on each parsed card.
        exclude_urls: URLs of ads to skip (usually the viewed ad itself).
        exclude_ad_ids: Ad-ids to skip.

    Returns:
        List of :class:`AdCard` objects from the seller's portfolio.
    """
    if isinstance(xml_source, ET.Element):
        root = xml_source
    else:
        text_or_path = str(xml_source)
        if text_or_path.lstrip().startswith("<"):
            root = ET.fromstring(text_or_path)
        else:
            root = ET.parse(text_or_path).getroot()
    if not _has_seller_section(root):
        return []
    cards = CardParser().parse(root, query=query)
    skip_urls = {u for u in exclude_urls if u}
    skip_ids = {i for i in exclude_ad_ids if i}
    return [
        card
        for card in cards
        if card.url not in skip_urls and card.ad_id not in skip_ids
    ]


class CompetitiveWatch:
    """Links market ads to own listings and grades competitive position."""

    def __init__(self, storage, threshold: float = _SIMILARITY_THRESHOLD):
        self.storage = storage
        self.threshold = threshold

    def refresh(
        self,
        own_ads: List[OwnAd],
        candidates: Optional[List[AdCard]] = None,
        seen_at: Optional[str] = None,
    ) -> Dict[str, object]:
        """(Re)link every own ad against its market candidates.

        Returns counts plus per-own-ad summaries with undercut information.
        """
        if candidates is None:
            candidates = self.storage.get_ads(active_only=True)
        now = seen_at or datetime.now(timezone.utc).isoformat()
        new_links = 0
        per_own: Dict[str, Dict[str, object]] = {}

        for own in own_ads:
            linked = 0
            cheaper = 0
            for candidate in candidates:
                score = link_score(own, candidate)
                if score < self.threshold:
                    continue
                is_new = self.storage.competitor_link_upsert(
                    own.fingerprint, candidate.fingerprint, score, seen_at=now
                )
                new_links += int(is_new)
                linked += 1
                if own.price and candidate.price and candidate.price < own.price:
                    cheaper += 1
            per_own[own.fingerprint] = {
                "title": own.title,
                "my_price": own.price,
                "linked_competitors": linked,
                "cheaper_competitors": cheaper,
                "query_hint": derive_query(own.title),
            }

        total = sum(len(self.storage.competitor_links(o.fingerprint)) for o in own_ads)
        return {"new_links": new_links, "total_links": total, "per_own": per_own}

    def observe_seller_ads(
        self,
        xml_source: Union[str, Path, ET.Element],
        my_ad: OwnAd,
        seen_at: Optional[str] = None,
        viewed_url: Optional[str] = None,
        viewed_ad_id: Optional[str] = None,
    ) -> Dict[str, object]:
        """Crawl a competitor's portfolio from their detail page.

        Parses the "other ads by this seller" block, stores every found card
        as a market observation (so price tracking keeps working for them),
        and links the ones similar enough to ``my_ad``.

        Pass ``viewed_url``/``viewed_ad_id`` of the detail page being
        scraped so the viewed competitor ad itself is excluded from the
        portfolio (the seller block typically re-shows it).

        Returns counts and the parsed portfolio.
        """
        now = seen_at or datetime.now(timezone.utc).isoformat()
        query = derive_query(my_ad.title)
        portfolio = parse_seller_ads(
            xml_source,
            query=query,
            exclude_urls=(viewed_url,) if viewed_url else (),
            exclude_ad_ids=(viewed_ad_id,) if viewed_ad_id else (),
        )
        stored = 0
        new_ads = 0
        if portfolio:
            _saved, new_fps = self.storage.save_ads_with_new(portfolio, seen_at=now)
            stored = len(portfolio)
            new_ads = len(new_fps)
        linked = 0
        new_links = 0
        for card in portfolio:
            score = link_score(my_ad, card)
            if score < self.threshold:
                continue
            is_new = self.storage.competitor_link_upsert(
                my_ad.fingerprint, card.fingerprint, score, seen_at=now
            )
            linked += 1
            new_links += int(is_new)
        return {
            "seller_ads_found": len(portfolio),
            "seller_ads_stored": stored,
            "new_market_ads": new_ads,
            "linked_competitors": linked,
            "new_links": new_links,
            "query_hint": query,
            "portfolio": [card.to_dict() for card in portfolio],
        }

    def report(self, own_fingerprint: str) -> Dict[str, object]:
        """Full competitive picture for one own listing."""
        links = self.storage.competitor_links(own_fingerprint)
        ads = {
            ad.fingerprint: ad for ad in self.storage.get_ads(limit=1000)
        }
        competitors: List[Dict[str, object]] = []
        for link in links:
            ad = ads.get(link["competitor_fingerprint"])
            entry = dict(link)
            if ad is not None:
                entry["ad"] = ad.to_dict()
            competitors.append(entry)

        prices = [
            entry["ad"]["price"]
            for entry in competitors
            if entry.get("ad") and entry["ad"].get("price") is not None
        ]
        prices.sort()
        return {
            "own_fingerprint": own_fingerprint,
            "competitors_count": len(competitors),
            "cheapest_price": prices[0] if prices else None,
            "most_expensive_price": prices[-1] if prices else None,
            "competitors": competitors,
        }

    def price_position(
        self, own: OwnAd, candidates: Optional[List[AdCard]] = None
    ) -> Dict[str, object]:
        """Where my price stands among similar ads (1 = cheapest)."""
        if candidates is None:
            candidates = self.storage.get_ads(active_only=True)
        similar = [
            card
            for card in candidates
            if card.price is not None
            and link_score(own, card) >= self.threshold
        ]
        prices = sorted(card.price for card in similar)
        if not prices or own.price is None:
            return {
                "rank": None,
                "of": len(prices),
                "cheaper_competitors": 0,
                "median_competitor_price": None,
            }
        cheaper = sum(1 for price in prices if price < own.price)
        mid = len(prices) // 2
        median = prices[mid] if len(prices) % 2 else (prices[mid - 1] + prices[mid]) / 2
        return {
            "rank": cheaper + 1,
            "of": len(prices) + 1,
            "cheaper_competitors": cheaper,
            "median_competitor_price": median,
        }
