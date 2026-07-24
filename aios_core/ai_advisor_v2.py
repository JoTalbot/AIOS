"""AI advisor v2 — cross-platform recommendation engine with price prediction.

Extends AISalesAdvisor with:
- Cross-platform price comparison (OLX ↔ Rozetka ↔ Prom ↔ Shafa)
- Price prediction (simple linear regression on sighting history)
- Best-deal recommendations (buy where cheapest, sell where priciest)
- Arbitrage opportunity detection

Reuses existing AISalesAdvisor + TemplateRegistry infrastructure.
"""

from __future__ import annotations

from dataclasses import dataclass

from aios_core.ai_advisor import AISalesAdvisor
from aios_core.cross_platform_comparator import CrossPlatformComparator


@dataclass
class CrossPlatformRecommendation:
    """Recommendation based on cross-platform price analysis."""

    product_title: str
    best_buy_platform: str | None = None
    best_buy_price: float | None = None
    best_sell_platform: str | None = None
    best_sell_price: float | None = None
    spread_pct: float | None = None
    arbitrage: bool = False
    recommendation_text: str = ""
    confidence: float = 0.0


@dataclass
class PricePrediction:
    """Simple linear regression price prediction from sighting history."""

    fingerprint: str
    title: str
    current_price: float
    predicted_price: float | None = None
    trend: str = "stable"  # "up", "down", "stable"
    slope: float = 0.0
    confidence: float = 0.0
    history_points: int = 0


class AICrossPlatformAdvisor:
    """Cross-platform recommendation engine extending AISalesAdvisor.

    Combines price comparison data with price prediction to provide:
    - Where to buy cheapest
    - Where to sell at highest price
    - Arbitrage opportunities
    - Price trend predictions
    """

    def __init__(
        self,
        advisor: AISalesAdvisor | None = None,
        comparator: CrossPlatformComparator | None = None,
    ) -> None:
        """Initialize AICrossPlatformAdvisor.

        Args:
            advisor: Existing AISalesAdvisor instance.
            comparator: CrossPlatformComparator for multi-platform analysis.
        """
        self.advisor = advisor or AISalesAdvisor()
        self.comparator = comparator or CrossPlatformComparator()

    def recommend_cross_platform(
        self,
        title: str,
        min_spread_pct: float = 5.0,
    ) -> CrossPlatformRecommendation | None:
        """Generate cross-platform buy/sell recommendation.

        Args:
            title: Product title to analyze.
            min_spread_pct: Minimum spread for arbitrage consideration.

        Returns:
            CrossPlatformRecommendation or None if insufficient data.
        """
        # Find comparison groups
        groups = self.comparator.compare(query=title)
        if not groups:
            return None

        # Find best matching group
        best_group = None
        best_sim = 0.0
        for group in groups:
            for p in group.products:
                sim = self.comparator._title_similarity(title, p.title)
                if sim > best_sim:
                    best_sim = sim
                    best_group = group

        if not best_group or not best_group.prices:
            return None

        prices = best_group.prices
        lowest = min(prices)
        highest = max(prices)

        # Find platforms
        best_buy_platform = best_group.best_platform
        best_sell_platform = None
        for p in best_group.products:
            if p.price == highest:
                best_sell_platform = p.platform
                break

        spread = best_group.spread_pct or 0
        arbitrage = spread >= min_spread_pct

        # Generate recommendation text
        if arbitrage:
            rec = (
                f"Арбитражная возможность: '{title}' — "
                f"купить на {best_buy_platform} за {lowest:.0f} грн, "
                f"продать на {best_sell_platform} за {highest:.0f} грн "
                f"(спред {spread:.1f}%)"
            )
        elif best_buy_platform:
            rec = f"Лучшая цена для '{title}' — {lowest:.0f} грн на {best_buy_platform}"
        else:
            rec = f"Данных недостаточно для рекомендации по '{title}'"

        confidence = min(0.95, 0.5 + best_sim * 0.3 + (len(prices) - 1) * 0.1)

        return CrossPlatformRecommendation(
            product_title=title,
            best_buy_platform=best_buy_platform,
            best_buy_price=lowest,
            best_sell_platform=best_sell_platform,
            best_sell_price=highest,
            spread_pct=spread,
            arbitrage=arbitrage,
            recommendation_text=rec,
            confidence=confidence,
        )

    def predict_price(
        self,
        storage,
        fingerprint: str,
        horizon_days: int = 7,
    ) -> PricePrediction | None:
        """Predict future price using simple linear regression on sighting history.

        Args:
            storage: Storage instance with sighting data.
            fingerprint: Product fingerprint.
            horizon_days: Number of days to predict ahead.

        Returns:
            PricePrediction or None if insufficient data.
        """
        history = storage.price_history(fingerprint)
        if len(history) < 3:
            return None

        # Simple linear regression: price = a * day + b
        prices = [h.get("price") for h in history]
        days = list(range(len(prices)))

        # Filter out None prices
        valid_points = [(d, p) for d, p in zip(days, prices, strict=False) if p is not None]
        if len(valid_points) < 3:
            return None

        # Compute slope and intercept
        n = len(valid_points)
        sum_x = sum(d for d, _ in valid_points)
        sum_y = sum(p for _, p in valid_points)
        sum_xy = sum(d * p for d, p in valid_points)
        sum_x2 = sum(d * d for d, _ in valid_points)

        denom = n * sum_x2 - sum_x * sum_x
        if denom == 0:
            return None

        slope = (n * sum_xy - sum_x * sum_y) / denom
        intercept = (sum_y - slope * sum_x) / n

        # Predict
        future_day = days[-1] + horizon_days
        predicted = slope * future_day + intercept

        # Trend
        if abs(slope) < 0.01 * intercept:
            trend = "stable"
        elif slope > 0:
            trend = "up"
        else:
            trend = "down"

        # Confidence: more data points → higher confidence
        confidence = min(0.95, 0.3 + n * 0.1)

        return PricePrediction(
            fingerprint=fingerprint,
            title=history[-1].get("fingerprint", fingerprint),
            current_price=prices[-1] if prices else 0,
            predicted_price=round(predicted, 2),
            trend=trend,
            slope=round(slope, 4),
            confidence=confidence,
            history_points=n,
        )

    def full_analysis(
        self,
        title: str,
        storage=None,
        fingerprint: str | None = None,
    ) -> dict[str, object]:
        """Complete cross-platform analysis: comparison + prediction + advice.

        Args:
            title: Product title.
            storage: Storage instance for price prediction.
            fingerprint: Optional specific fingerprint for prediction.

        Returns:
            Dict with cross_platform_recommendation, price_prediction, and price_advice.
        """
        result: dict[str, object] = {"title": title}

        # 1. Cross-platform recommendation
        rec = self.recommend_cross_platform(title)
        result["cross_platform_recommendation"] = rec.__dict__ if rec else None

        # 2. Price prediction (if storage available)
        if storage and fingerprint:
            pred = self.predict_price(storage, fingerprint)
            result["price_prediction"] = pred.__dict__ if pred else None
        else:
            result["price_prediction"] = None

        # 3. Price advice (from existing advisor)
        if storage and fingerprint:
            ads = storage.get_ads()
            ad = None
            for a in ads:
                if a.fingerprint == fingerprint:
                    ad = a
                    break
            if ad and ad.price:
                advice = self.advisor.price_advice("multi", fingerprint, ad.price)
                result["price_advice"] = advice.__dict__ if advice else None
            else:
                result["price_advice"] = None
        else:
            result["price_advice"] = None

        return result
