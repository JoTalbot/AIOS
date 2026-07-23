"""test_kan_scenario test."""
from aios_core.kan import KANetwork

def test_kan():
    s = KANetwork().stats()
    assert isinstance(s, dict)

