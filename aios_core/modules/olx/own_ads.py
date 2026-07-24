"""AIOS OLX Android Agent — own listings control ("Мої оголошення")."""

from __future__ import annotations

import hashlib
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from .text_utils import normalize_text, parse_price

_VIEWS_RE = re.compile(r"(?:переглядів?|просмотр\w*)\s*:?\s*(\d+)", re.IGNORECASE)
_FAV_RE = re.compile(r"(?:в обраних|в избранн\w*)\s*:?\s*(\d+)", re.IGNORECASE)
_MSG_RE = re.compile(r"(?:повідомлен\w*|сообщени\w*)\s*:?\s*(\d+)", re.IGNORECASE)
_CARD_MARKERS = ("myad", "mylisting", "my_ad")
_AD_ID_RE = re.compile(r"ID([A-Za-z0-9]{4,})\.html")
_INACTIVE_MARKERS = ("неактивн", "деактивов", "знят", "архів")


@dataclass
class OwnAd:
    """One of my listings with its public counters."""

    title: str
    price: float | None = None
    currency: str | None = None
    views: int = 0
    favorites: int = 0
    messages: int = 0
    status: str = "active"
    url: str | None = None
    ad_id: str | None = None

    @property
    def fingerprint(self) -> str:
        """Execute fingerprint."""
        if self.ad_id:
            base = f"own:id:{self.ad_id.strip().lower()}"
        elif self.url:
            base = f"own:url:{self.url.strip().lower()}"
        else:
            base = f"own:{(self.title or '').strip().lower()}"
        return hashlib.sha256(base.encode("utf-8")).hexdigest()[:12]

    def to_dict(self) -> dict[str, object]:
        """Serialize to dict."""
        return {
            "fingerprint": self.fingerprint,
            "title": self.title,
            "price": self.price,
            "currency": self.currency,
            "views": self.views,
            "favorites": self.favorites,
            "messages": self.messages,
            "status": self.status,
            "url": self.url,
            "ad_id": self.ad_id,
        }


class OwnAdsParser:
    """Parses the 'My listings' screen into :class:`OwnAd` rows."""

    def parse(self, xml_source: str | Path | ET.Element) -> list[OwnAd]:
        """Execute parse."""
        if isinstance(xml_source, ET.Element):
            root = xml_source
        else:
            text_or_path = str(xml_source)
            root = (
                ET.fromstring(text_or_path)
                if text_or_path.lstrip().startswith("<")
                else ET.parse(text_or_path).getroot()
            )

        ads: list[OwnAd] = []
        for node in root.iter("node"):
            resource_id = (node.attrib.get("resource-id") or "").lower()
            if not any(marker in resource_id for marker in _CARD_MARKERS):
                continue
            texts: list[str] = []
            url: str | None = None
            ad_id: str | None = None
            for child in node.iter():
                text = normalize_text(child.attrib.get("text"))
                if text:
                    texts.append(text)
                for value in child.attrib.values():
                    if "olx." in value and url is None:
                        url = value
                    match = _AD_ID_RE.search(value)
                    if match:
                        ad_id = match.group(1)
            ad = self.ad_from_texts(texts, url=url, ad_id=ad_id)
            if ad.title:
                ads.append(ad)
        return ads

    @staticmethod
    def ad_from_texts(
        texts: list[str],
        url: str | None = None,
        ad_id: str | None = None,
    ) -> OwnAd:
        """Classify texts of one own-ad card: price/counters/status by shape,
        first remaining text becomes the title."""
        ad = OwnAd(title="", url=url, ad_id=ad_id)
        for raw in texts:
            lowered = raw.lower()
            if ad.price is None:
                parsed = parse_price(raw)
                if parsed is not None:
                    ad.price, ad.currency = parsed
                    continue
            views = _VIEWS_RE.search(raw)
            if views:
                ad.views = int(views.group(1))
                continue
            fav = _FAV_RE.search(raw)
            if fav:
                ad.favorites = int(fav.group(1))
                continue
            msgs = _MSG_RE.search(raw)
            if msgs:
                ad.messages = int(msgs.group(1))
                continue
            if any(marker in lowered for marker in _INACTIVE_MARKERS):
                ad.status = "inactive"
                continue
            if not ad.title:
                ad.title = raw
        return ad


class OwnAdsTracker:
    """Records snapshots of own-ad counters and finds stagnant listings."""

    def __init__(self, storage):
        """Initialize OwnAdsTracker."""
        self.storage = storage

    def record_snapshot(
        self, ads: list[OwnAd], seen_at: str | None = None
    ) -> dict[str, object]:
        """Persist one snapshot of all own ads; reports counter deltas."""
        now = seen_at or datetime.now(UTC).isoformat()
        result: dict[str, object] = {"recorded": len(ads), "new": 0, "deltas": {}}
        for ad in ads:
            is_new = self.storage.upsert_own_ad(ad, seen_at=now)
            if is_new:
                result["new"] += 1
                continue
            history = self.storage.own_ad_history(ad.fingerprint)
            if len(history) >= 2:
                previous, latest = history[-2], history[-1]
                result["deltas"][ad.fingerprint] = {
                    "title": ad.title,
                    "views_delta": (latest["views"] or 0) - (previous["views"] or 0),
                    "favorites_delta": (latest["favorites"] or 0)
                    - (previous["favorites"] or 0),
                    "messages_delta": (latest["messages"] or 0)
                    - (previous["messages"] or 0),
                }
        return result

    def stagnant(
        self,
        min_age_days: float = 3.0,
        min_views_per_day: float = 1.0,
        now: datetime | None = None,
    ) -> list[dict[str, object]]:
        """Listings old enough to judge but getting too few views per day."""
        now = now or datetime.now(UTC)
        report: list[dict[str, object]] = []
        for row in self.storage.own_ads(status="active"):
            first_seen = row.get("first_seen_at")
            if not first_seen:
                continue
            age_days = (
                now - datetime.fromisoformat(first_seen)
            ).total_seconds() / 86400.0
            if age_days < min_age_days:
                continue
            views_total = row.get("last_views") or 0
            views_per_day = views_total / age_days if age_days else float("inf")
            if views_per_day >= min_views_per_day:
                continue
            report.append(
                {
                    "fingerprint": row["fingerprint"],
                    "title": row["title"],
                    "age_days": round(age_days, 2),
                    "views_total": views_total,
                    "views_per_day": round(views_per_day, 3),
                    "reason": (
                        f"{views_total} переглядів за {round(age_days, 1)} дн. "
                        f"({round(views_per_day, 2)}/день < {min_views_per_day}/день)"
                    ),
                }
            )
        report.sort(key=lambda item: item["views_per_day"])
        return report
