"""test_moe_scenario test."""
from aios_core.moe import MixtureOfExperts

def test_moe():
    s = MixtureOfExperts().stats()
    assert isinstance(s, dict)

