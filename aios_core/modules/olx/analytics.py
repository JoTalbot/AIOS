"""AIOS OLX Android Agent — competitor analysis, price tracking and
listing recommendations."""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field
from statistics import mean, median
from typing import Dict, List, Optional, Tuple

from .models import AdCard

_STOPWORDS = {
    # Ukrainian / Russian filler words frequent in listings.
    "для",
    "або",
    "та",
    "і",
    "й",
    "на",
    "в",
    "у",
    "з",
    "зі",
    "до",
    "по",
    "що",
    "це",
    "як",
    "не",
    "від",
    "під",
    "над",
    "при",
    "без",
    "про",
    "и",
    "а",
    "о",
    "с",
    "со",
    "к",
    "во",
    "из",
    "за",
    "от",
    "у",
    "буде",
    "стан",
    "новый",
    "нова",
    "нове",
    "новий",
    "б/у",
    "бу",
    "продам",
    "продаж",
    "куплю",
    "срочно",
    "гарний",
    "хороший",
}

_TOKEN_RE = re.compile(r"[0-9A-Za-zА-Яа-яІіЇїЄєҐґ'-]+")


def _tokenize(text: str) -> List[str]:
    return [
        token
        for token in _TOKEN_RE.findall(text.lower())
        if len(token) >= 4 and token not in _STOPWORDS and not token.isdigit()
    ]


@dataclass
class CompetitorReport:
    """Aggregated market picture for a set of competing listings."""

    query: Optional[str]
    total_ads: int
    priced_ads: int
    min_price: Optional[float]
    max_price: Optional[float]
    mean_price: Optional[float]
    median_price: Optional[float]
    top_share: float
    top_cities: List[Tuple[str, int]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, object]:
        """Serialize to dict."""
        return {
            "query": self.query,
            "total_ads": self.total_ads,
            "priced_ads": self.priced_ads,
            "min_price": self.min_price,
            "max_price": self.max_price,
            "mean_price": self.mean_price,
            "median_price": self.median_price,
            "top_share": self.top_share,
            "top_cities": list(self.top_cities),
        }


class CompetitorAnalyzer:
    """Builds :class:`CompetitorReport` statistics from collected cards."""

    def analyze(self, ads: List[AdCard], query: Optional[str] = None) -> CompetitorReport:
        """Execute analyze."""
        prices = [ad.price for ad in ads if ad.price is not None]
        cities = Counter(ad.city for ad in ads if ad.city)
        top_count = sum(1 for ad in ads if ad.is_top)
        total = len(ads)

        return CompetitorReport(
            query=query,
            total_ads=total,
            priced_ads=len(prices),
            min_price=min(prices) if prices else None,
            max_price=max(prices) if prices else None,
            mean_price=round(mean(prices), 2) if prices else None,
            median_price=median(prices) if prices else None,
            top_share=round(top_count / total, 4) if total else 0.0,
            top_cities=cities.most_common(10),
        )

    def price_percentile(self, ads: List[AdCard], price: float) -> Optional[float]:
        """Share of priced listings cheaper than or equal to ``price``.

        ``0.8`` means your price is cheaper than 80% of the market.
        """
        prices = [ad.price for ad in ads if ad.price is not None]
        if not prices:
            return None
        cheaper = sum(1 for value in prices if value <= price)
        return round(cheaper / len(prices), 4)


@dataclass
class Recommendation:
    """Actionable advice for placing an ad against the current market."""

    query: Optional[str]
    my_title: Optional[str]
    my_price: Optional[float]
    suggested_price: Optional[float]
    verdict: str
    title_keywords: List[str] = field(default_factory=list)
    use_top_promotion: bool = False
    notes: List[str] = field(default_factory=list)

    def to_text(self) -> str:
        """Execute to text."""
        lines = [f"Рекомендації для оголошення (запит: {self.query or '—'})"]
        if self.suggested_price is not None:
            lines.append(f"- Рекомендована ціна: {self.suggested_price:g}")
        lines.append(f"- Оцінка ціни: {self.verdict}")
        if self.title_keywords:
            lines.append("- Ключові слова для заголовка: " + ", ".join(self.title_keywords))
        top_verdict = "так" if self.use_top_promotion else "не обов'язково"
        lines.append(f"- TOP-просування: {top_verdict}")
        for note in self.notes:
            lines.append(f"- {note}")
        return "\n".join(lines)


class RecommendationEngine:
    """Generates listing advice from collected competitor data."""

    def recommend(
        self,
        ads: List[AdCard],
        my_ad: Optional[AdCard] = None,
        undercut_ratio: float = 0.97,
    ) -> Recommendation:
        """Suggest a price, title keywords and promotion strategy.

        Args:
            ads: Collected competitor cards (usually for one search query).
            my_ad: Your draft listing (title/price) to evaluate; optional.
            undercut_ratio: Suggested price = median competitor price × ratio.
        """
        my_price = my_ad.price if my_ad else None
        my_title = my_ad.title if my_ad else None
        prices = [ad.price for ad in ads if ad.price is not None]

        suggested_price: Optional[float] = None
        verdict = "unknown"
        notes: List[str] = []

        if prices:
            market_median = median(prices)
            suggested_price = round(market_median * undercut_ratio)
            if my_price is not None:
                if my_price <= market_median * 0.9:
                    verdict = "below_market"
                    notes.append("Ціна нижча за ринок — можна підняти без втрати інтересу.")
                elif my_price >= market_median * 1.1:
                    verdict = "above_market"
                    notes.append(
                        f"Ціна вища за медіану ринку ({market_median:g}) — очікуйте менше відгуків."
                    )
                else:
                    verdict = "competitive"
        else:
            notes.append("Недостатньо цін у конкурентів для оцінки.")

        keywords = self._title_keywords(ads, my_title)

        top_ads = [ad for ad in ads if ad.is_top and ad.price is not None]
        plain_ads = [ad for ad in ads if not ad.is_top and ad.price is not None]
        use_top = False
        if len(top_ads) >= 3:
            use_top = True
        elif (
            top_ads
            and plain_ads
            and median([a.price for a in top_ads]) >= median([a.price for a in plain_ads])
        ):
            use_top = True
        if use_top:
            notes.append("TOP-оголошення помітні у видачі — просування виправдане.")

        cities = Counter(ad.city for ad in ads if ad.city)
        if cities:
            city, count = cities.most_common(1)[0]
            notes.append(f"Найактивніший регіон запиту: {city} ({count} оголошень).")

        return Recommendation(
            query=(my_ad.query if my_ad else None),
            my_title=my_title,
            my_price=my_price,
            suggested_price=suggested_price,
            verdict=verdict,
            title_keywords=keywords,
            use_top_promotion=use_top,
            notes=notes,
        )

    @staticmethod
    def _title_keywords(ads: List[AdCard], my_title: Optional[str]) -> List[str]:
        """Frequent tokens from the cheaper half of listings missing in my title."""
        priced = sorted(
            (ad for ad in ads if ad.price is not None and ad.title),
            key=lambda ad: ad.price,
        )
        if len(priced) >= 2:
            priced = priced[: max(2, len(priced) // 2)]
        counter: Counter = Counter()
        for ad in priced:
            counter.update(set(_tokenize(ad.title)))
        mine = set(_tokenize(my_title)) if my_title else set()
        return [word for word, _count in counter.most_common(20) if word not in mine][:10]


@dataclass
class PriceChange:
    """A detected price movement for a single tracked ad."""

    fingerprint: str
    title: str
    url: Optional[str]
    city: Optional[str]
    query: Optional[str]
    first_price: float
    last_price: float
    change_pct: float
    sightings: int
    last_seen_at: Optional[str]

    def to_dict(self) -> Dict[str, object]:
        """Serialize to dict."""
        return {
            "fingerprint": self.fingerprint,
            "title": self.title,
            "url": self.url,
            "city": self.city,
            "query": self.query,
            "first_price": self.first_price,
            "last_price": self.last_price,
            "change_pct": self.change_pct,
            "sightings": self.sightings,
            "last_seen_at": self.last_seen_at,
        }


class PriceTracker:
    """Analyses sighting history: price drops and ads that left the feed."""

    def __init__(self, storage):
        self.storage = storage

    def price_drops(
        self, query: Optional[str] = None, threshold_pct: float = -0.005
    ) -> List[PriceChange]:
        """Ads whose latest sighted price is below the first sighted price.

        Args:
            query: Restrict to one search query (None = the whole store).
            threshold_pct: Relative change cut-off; -0.005 = at least 0.5% down.

        Returns:
            Changes sorted by relative drop, biggest first.
        """
        drops: List[PriceChange] = []
        for ad in self.storage.get_ads(query=query):
            history = self.storage.price_history(ad.fingerprint)
            prices = [(point["seen_at"], point["price"]) for point in history if point["price"]]
            if len(prices) < 2:
                continue
            first_price = prices[0][1]
            last_price = prices[-1][1]
            change_pct = (last_price - first_price) / first_price
            if change_pct <= threshold_pct:
                drops.append(
                    PriceChange(
                        fingerprint=ad.fingerprint,
                        title=ad.title,
                        url=ad.url,
                        city=ad.city,
                        query=ad.query,
                        first_price=first_price,
                        last_price=last_price,
                        change_pct=round(change_pct, 4),
                        sightings=len(history),
                        last_seen_at=prices[-1][0],
                    )
                )
        drops.sort(key=lambda change: change.change_pct)
        return drops

    def gone_from_feed(self, query: Optional[str] = None) -> List[AdCard]:
        """Ads marked inactive (vanished from the feed — sold or removed)."""
        return self.storage.get_ads(query=query, active_only=False)
