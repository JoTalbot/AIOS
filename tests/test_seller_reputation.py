"""Tests for seller reputation scoring."""

from __future__ import annotations

from aios_core.modules.olx.models import AdCard
from aios_core.modules.olx.storage import OLXStorage
from aios_core.seller_reputation import (
    SellerProfile,
    SellerReputationScorer,
    SellerScore,
)


def _card(title: str, price: float, ad_id: str = "", city: str = "Kyiv") -> AdCard:
    return AdCard(title=title, price=price, currency="UAH", city=city,
                  published_text="today", is_top=False, url=f"https://test.ua/{title}",
                  ad_id=ad_id or f"id-{title}", query="test", raw_texts=[title])


def test_seller_score_dataclass():
    """SellerScore has all fields."""
    score = SellerScore(
        seller_id="seller1", composite_score=75.0, grade="B",
        response_time_score=50, listing_quality_score=80,
        price_consistency_score=70, activity_score=60,
    )
    d = score.to_dict()
    assert d["seller_id"] == "seller1"
    assert d["grade"] == "B"
    assert d["composite_score"] == 75.0


def test_seller_profile_dataclass():
    """SellerProfile has basic fields."""
    profile = SellerProfile(seller_id="s1", name="Test Seller", total_ads=10)
    d = profile.to_dict()
    assert d["seller_id"] == "s1"
    assert d["total_ads"] == 10


def test_seller_reputation_empty():
    """Scorer returns None for empty storage."""
    storage = OLXStorage(":memory:")
    scorer = SellerReputationScorer(storage)
    score = scorer.score_seller()
    assert score is None


def test_seller_reputation_single_seller():
    """Scorer computes score for a seller with ads."""
    storage = OLXStorage(":memory:")
    storage.save_ads([
        _card("iPhone 15", 30000, ad_id="seller1"),
        _card("iPhone 16", 35000, ad_id="seller1"),
        _card("MacBook", 50000, ad_id="seller1"),
    ])
    scorer = SellerReputationScorer(storage)
    score = scorer.score_seller("seller1")

    assert score is not None
    assert score.composite_score > 0
    assert score.grade in ("A", "B", "C", "D", "F")


def test_seller_reputation_grade_thresholds():
    """Grading thresholds are correct."""
    scorer = SellerReputationScorer(OLXStorage(":memory:"))
    assert scorer._grade(95) == "A"
    assert scorer._grade(80) == "B"
    assert scorer._grade(65) == "C"
    assert scorer._grade(45) == "D"
    assert scorer._grade(20) == "F"


def test_seller_reputation_activity():
    """Activity score increases with more ads."""
    scorer = SellerReputationScorer(OLXStorage(":memory:"))
    assert scorer._compute_activity([]) == 0
    assert scorer._compute_activity([1] * 1) == 35
    assert scorer._compute_activity([1] * 5) == 95
    assert scorer._compute_activity([1] * 15) == 100


def test_seller_reputation_price_consistency():
    """Price consistency score penalizes volatile prices."""
    scorer = SellerReputationScorer(OLXStorage(":memory:"))
    # Stable prices
    ads_stable = [_card("P", 1000, ad_id="s"), _card("P", 1000, ad_id="s")]
    assert scorer._compute_price_consistency(ads_stable) >= 80

    # Variable prices
    ads_var = [_card("P", 1000, ad_id="s"), _card("P", 5000, ad_id="s")]
    assert scorer._compute_price_consistency(ads_var) < 50


def test_seller_reputation_score_all():
    """score_all_sellers returns list sorted by score."""
    storage = OLXStorage(":memory:")
    storage.save_ads([
        _card("Product A", 100, ad_id="seller_a"),
        _card("Product B", 500, ad_id="seller_b"),
    ])
    scorer = SellerReputationScorer(storage)
    scores = scorer.score_all_sellers()
    assert len(scores) >= 1
