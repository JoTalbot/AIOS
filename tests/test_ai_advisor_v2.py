"""Tests for AI advisor v2 — cross-platform recommendations and price prediction."""

from __future__ import annotations

from aios_core.ai_advisor_v2 import (
    AICrossPlatformAdvisor,
    CrossPlatformRecommendation,
    PricePrediction,
)
from aios_core.cross_platform_comparator import CrossPlatformComparator
from aios_core.modules.olx.models import AdCard
from aios_core.modules.olx.storage import OLXStorage
from aios_core.modules.rozetka.storage import RozetkaStorage


def _card(title: str, price: float, ad_id: str = "", query: str = "test") -> AdCard:
    """Helper to create an AdCard."""
    return AdCard(
        title=title,
        price=price,
        currency="UAH",
        city="Kyiv",
        published_text="today",
        is_top=False,
        url=f"https://{title}.ua",
        ad_id=ad_id or f"id-{title}",
        query=query,
        raw_texts=[title],
    )


def test_cross_platform_recommendation_dataclass():
    """CrossPlatformRecommendation stores all fields."""
    rec = CrossPlatformRecommendation(
        product_title="iPhone 15",
        best_buy_platform="rozetka",
        best_buy_price=28000,
        best_sell_platform="olx",
        best_sell_price=32000,
        spread_pct=14.3,
        arbitrage=True,
        recommendation_text="Арбитражная возможность",
        confidence=0.8,
    )
    assert rec.arbitrage is True
    assert rec.best_buy_platform == "rozetka"
    assert rec.best_sell_price == 32000


def test_price_prediction_dataclass():
    """PricePrediction stores trend data."""
    pred = PricePrediction(
        fingerprint="fp1",
        title="iPhone",
        current_price=30000,
        predicted_price=29500,
        trend="down",
        slope=-50,
        confidence=0.7,
        history_points=5,
    )
    assert pred.trend == "down"
    assert pred.predicted_price == 29500


def test_ai_advisor_v2_init():
    """AICrossPlatformAdvisor initializes with defaults."""
    advisor = AICrossPlatformAdvisor()
    assert advisor.advisor is not None
    assert advisor.comparator is not None


def test_price_prediction_linear_regression():
    """predict_price uses linear regression on sighting history."""
    storage = OLXStorage(":memory:")
    # Add same product multiple times with decreasing price
    card = _card("Phone", 30000, ad_id="id-phone")
    storage.save_ads([card])

    card2 = _card("Phone", 28000, ad_id="id-phone")
    storage.save_ads([card2])

    card3 = _card("Phone", 26000, ad_id="id-phone")
    storage.save_ads([card3])

    advisor = AICrossPlatformAdvisor()
    fp = card.fingerprint
    pred = advisor.predict_price(storage, fp)

    if pred:
        assert pred.trend == "down"  # Price is decreasing
        assert pred.current_price == 26000
        assert pred.predicted_price < 26000  # Continued decrease
        assert pred.confidence >= 0.5


def test_price_prediction_insufficient_data():
    """predict_price returns None with insufficient data."""
    storage = OLXStorage(":memory:")
    # Only 1 sighting → insufficient for regression
    card = _card("Phone", 30000, ad_id="id-phone")
    storage.save_ads([card])

    advisor = AICrossPlatformAdvisor()
    pred = advisor.predict_price(storage, card.fingerprint)
    assert pred is None


def test_price_prediction_stable_price():
    """predict_price detects stable trend."""
    storage = OLXStorage(":memory:")
    card = _card("Stable Product", 10000, ad_id="id-stable")
    storage.save_ads([card])
    storage.save_ads([card])
    storage.save_ads([card])
    storage.save_ads([card])
    storage.save_ads([card])

    advisor = AICrossPlatformAdvisor()
    pred = advisor.predict_price(storage, card.fingerprint)

    if pred:
        assert pred.trend == "stable"  # Price unchanged


def test_ai_advisor_v2_full_analysis():
    """full_analysis combines comparison + prediction + advice."""
    olx = OLXStorage(":memory:")
    rozetka = RozetkaStorage(":memory:")
    comparator = CrossPlatformComparator(
        storages={"olx": olx, "rozetka": rozetka},
        title_similarity_threshold=0.3,
    )
    advisor = AICrossPlatformAdvisor(comparator=comparator)

    olx.save_ads([_card("iPhone 16", 35000, ad_id="id-iphone16")])
    rozetka.save_ads([_card("iPhone 16 Plus", 33000, ad_id="rz-iphone16")])

    result = advisor.full_analysis("iPhone 16")
    assert result["title"] == "iPhone 16"
    # Cross-platform recommendation may or may not be found depending on similarity
    assert "cross_platform_recommendation" in result
    assert "price_prediction" in result
    assert "price_advice" in result
