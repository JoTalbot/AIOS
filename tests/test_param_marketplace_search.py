"""Parametrized marketplace search."""
import pytest
from aios_core.marketplace import Marketplace

@pytest.mark.parametrize("query", ["test", "", "python", "ai", "quantum", "blockchain"])
def test_search_queries(query):
    m = Marketplace()
    r = m.search(query)
    assert isinstance(r, list)
