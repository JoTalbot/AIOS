"""Tests for aios_core/search.py"""
from __future__ import annotations
import pytest
from aios_core.search import SimpleSearchEngine


@pytest.fixture()
def engine():
    return SimpleSearchEngine()


class TestSimpleSearchEngine:
    def test_create(self, engine):
        assert engine is not None

    def test_index(self, engine):
        engine.index(doc_id="d1", text="machine learning tutorial")

    def test_add_document(self, engine):
        engine.add_document(doc_id="d1", text="deep learning basics", metadata={"tag": "ml"})

    def test_search(self, engine):
        engine.index(doc_id="d1", text="machine learning")
        engine.index(doc_id="d2", text="deep learning")
        results = engine.search(query="learning")
        assert isinstance(results, list)

    def test_search_empty(self, engine):
        results = engine.search(query="nothing")
        assert isinstance(results, list)

    def test_remove_document(self, engine):
        engine.index(doc_id="d1", text="test doc")
        engine.remove_document("d1")

    def test_get_document(self, engine):
        engine.index(doc_id="d1", text="hello world")
        doc = engine.get_document("d1")
        assert doc is not None

    def test_get_nonexistent(self, engine):
        assert engine.get_document("nope") is None

    def test_stats(self, engine):
        s = engine.stats()
        assert isinstance(s, dict)
