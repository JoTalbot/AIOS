"""AIOS OLX Android Agent — data model for parsed ad cards."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class AdCard:
    """A single OLX listing card parsed from a UIAutomator XML dump.

    Attributes:
        title: Listing title text.
        price: Numeric price value or ``None`` for negotiable/free listings.
        currency: ISO-like currency code (``UAH``, ``USD``, ``EUR``).
        city: Seller city as shown on the card.
        published_text: Raw publication label (e.g. ``"Сьогодні в 11:26"``).
        published_at: Normalised ISO-8601 publication timestamp, when parseable.
        is_top: Whether the card carries a TOP promotion badge.
        ad_id: OLX internal listing identifier, when extractable.
        url: Direct listing URL, when extractable from the dump.
        query: Search query that produced this card.
        raw_texts: All raw text values collected from the card subtree.
    """

    title: str
    price: Optional[float] = None
    currency: Optional[str] = None
    city: Optional[str] = None
    published_text: Optional[str] = None
    published_at: Optional[str] = None
    is_top: bool = False
    ad_id: Optional[str] = None
    url: Optional[str] = None
    query: Optional[str] = None
    raw_texts: List[str] = field(default_factory=list)

    @property
    def fingerprint(self) -> str:
        """Stable identity hash for an ad across collection runs.

        Resolution order: ``ad_id`` → ``url`` → ``title|city|query``.
        The price is deliberately *not* part of the identity so that price
        changes are tracked as history of one ad instead of creating a new
        ad on every edit. The query stays in the composite identity so the
        same physical ad found via different searches is tracked per query.
        """
        if self.ad_id:
            base = f"id:{self.ad_id.strip().lower()}|{(self.query or '').strip().lower()}"
        elif self.url:
            base = f"url:{self.url.strip().lower()}|{(self.query or '').strip().lower()}"
        else:
            base = "|".join(
                [
                    (self.title or "").strip().lower(),
                    (self.city or "").strip().lower(),
                    (self.query or "").strip().lower(),
                ]
            )
        return hashlib.sha256(base.encode("utf-8")).hexdigest()[:16]

    def to_dict(self) -> Dict[str, Any]:
        """Serialise the card to a plain dictionary."""
        return {
            "fingerprint": self.fingerprint,
            "title": self.title,
            "price": self.price,
            "currency": self.currency,
            "city": self.city,
            "published_text": self.published_text,
            "published_at": self.published_at,
            "is_top": self.is_top,
            "ad_id": self.ad_id,
            "url": self.url,
            "query": self.query,
            "raw_texts": list(self.raw_texts),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AdCard":
        """Reconstruct a card from :meth:`to_dict` output."""
        return cls(
            title=data.get("title") or "",
            price=data.get("price"),
            currency=data.get("currency"),
            city=data.get("city"),
            published_text=data.get("published_text"),
            published_at=data.get("published_at"),
            is_top=bool(data.get("is_top", False)),
            ad_id=data.get("ad_id"),
            url=data.get("url"),
            query=data.get("query"),
            raw_texts=list(data.get("raw_texts") or []),
        )

    def __str__(self) -> str:  # pragma: no cover - convenience only
        price = f"{self.price:g} {self.currency}" if self.price is not None else "—"
        city = self.city or "?"
        return f"{self.title} — {price} — {city}"
