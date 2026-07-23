"""Tests for data infrastructure — lake, vector store, text utils, cache."""

from aios_core.data_lake import DataLake
from aios_core.vector_store import VectorStore
from aios_core.cache import CacheManager


def test_data_lake_stats():
    dl = DataLake()
    s = dl.stats()
    assert isinstance(s, dict)


def test_vector_store_stats():
    vs = VectorStore()
    s = vs.stats()
    assert isinstance(s, dict)


def test_cache_manager_stats():
    cm = CacheManager()
    s = cm.stats()
    assert isinstance(s, dict)
