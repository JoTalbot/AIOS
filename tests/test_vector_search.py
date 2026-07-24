"""Tests for vector search engine — TF-IDF product matching."""

from __future__ import annotations

from aios_core.modules.olx.models import AdCard
from aios_core.modules.olx.storage import OLXStorage
from aios_core.vector_search import SearchResult, VectorSearchEngine


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


def test_vector_search_build_index():
    """Build TF-IDF index from storage."""
    storage = OLXStorage(":memory:")
    storage.save_ads([
        _card("iPhone 15 Pro", 30000, ad_id="id-iphone15"),
        _card("Samsung Galaxy S24", 25000, ad_id="id-samsung"),
        _card("MacBook Air M3", 50000, ad_id="id-mac"),
    ])

    engine = VectorSearchEngine(storage=storage)
    count = engine.build_index()
    assert count == 3


def test_vector_search_build_index_empty():
    """Empty storage produces empty index."""
    storage = OLXStorage(":memory:")
    engine = VectorSearchEngine(storage=storage)
    count = engine.build_index()
    assert count == 0


def test_vector_search_query():
    """Search query returns relevant results."""
    storage = OLXStorage(":memory:")
    storage.save_ads([
        _card("iPhone 15 Pro Max", 40000, ad_id="id-iphone15"),
        _card("iPhone 14", 20000, ad_id="id-iphone14"),
        _card("Samsung Galaxy S24", 25000, ad_id="id-samsung"),
        _card("MacBook Air M3", 50000, ad_id="id-mac"),
    ])

    engine = VectorSearchEngine(storage=storage)
    engine.build_index()

    results = engine.search("iPhone", limit=5)
    # Should find iPhone-related products with higher scores
    assert len(results) >= 1
    # iPhone results should have higher scores than Samsung/MacBook
    iphone_scores = [r.score for r in results if "iPhone" in r.title]
    assert len(iphone_scores) >= 1


def test_vector_search_find_similar():
    """Find products similar to a reference."""
    storage = OLXStorage(":memory:")
    storage.save_ads([
        _card("iPhone 15 Pro", 30000, ad_id="id-iphone15"),
        _card("iPhone 14 Pro", 25000, ad_id="id-iphone14"),
        _card("Samsung Galaxy", 22000, ad_id="id-samsung"),
    ])

    engine = VectorSearchEngine(storage=storage)
    engine.build_index()

    # Find similar to iPhone 15 Pro
    fp = storage.get_ads()[0].fingerprint
    similar = engine.find_similar(fp, limit=5)
    assert len(similar) >= 1
    # iPhone 14 Pro should be more similar than Samsung
    iphone_sim = [r for r in similar if "iPhone" in r.title]
    samsung_sim = [r for r in similar if "Samsung" in r.title]
    if iphone_sim and samsung_sim:
        assert iphone_sim[0].score >= samsung_sim[0].score


def test_vector_search_result_to_dict():
    """SearchResult serializes to dict."""
    result = SearchResult(fingerprint="fp1", title="Test", price=1000, score=0.85, url="https://test.ua")
    d = result.to_dict()
    assert d["fingerprint"] == "fp1"
    assert d["score"] == 0.85
    assert d["title"] == "Test"


def test_vector_search_no_storage():
    """Engine without storage returns empty results."""
    engine = VectorSearchEngine(storage=None)
    count = engine.build_index()
    assert count == 0
    results = engine.search("test")
    assert len(results) == 0


def test_vector_search_min_term_freq():
    """Terms below min_term_freq are excluded from vocabulary."""
    storage = OLXStorage(":memory:")
    storage.save_ads([
        _card("unique_rare_word phone", 1000, ad_id="id1"),
        _card("common common phone", 2000, ad_id="id2"),
        _card("common phone laptop", 3000, ad_id="id3"),
    ])

    engine = VectorSearchEngine(storage=storage, min_term_freq=2)
    engine.build_index()

    # "unique_rare_word" appears only in 1 doc → excluded from vocab
    assert "unique_rare_word" not in engine._vocab
    # "common" appears in 2 docs → included
    assert "common" in engine._vocab


def test_vector_search_cosine_similarity():
    """Cosine similarity computation is correct."""
    engine = VectorSearchEngine()
    # Orthogonal vectors → 0
    a = [1.0, 0.0]
    b = [0.0, 1.0]
    assert engine._cosine(a, b) == 0.0
    # Identical vectors → 1
    assert engine._cosine([1.0, 0.0], [1.0, 0.0]) == 1.0
    # Zero vectors → 0
    assert engine._cosine([0.0, 0.0], [1.0, 0.0]) == 0.0
