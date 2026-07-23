"""test_creativity_scenario test."""
from aios_core.creativity import CreativeEngine

def test_creative():
    s = CreativeEngine().stats()
    assert isinstance(s, dict)

