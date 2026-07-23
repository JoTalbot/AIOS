"""test_mamba_scenario test."""
from aios_core.mamba import MambaModel

def test_mamba():
    s = MambaModel().stats()
    assert isinstance(s, dict)

