"""test_retnet_scenario test."""
from aios_core.retnet import RetNet

def test_retnet():
    s = RetNet().stats()
    assert isinstance(s, dict)

