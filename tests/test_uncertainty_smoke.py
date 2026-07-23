"""uncertainty smoke test."""
def test_uq(): from aios_core.uncertainty import UncertaintyQuantifier; assert UncertaintyQuantifier().stats() is not None
