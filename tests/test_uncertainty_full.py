"""Uncertainty full ops."""
from aios_core.uncertainty import UncertaintyQuantifier
def test_uq(): s=UncertaintyQuantifier().stats(); assert isinstance(s,dict)
