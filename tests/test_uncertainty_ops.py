from aios_core.uncertainty import UncertaintyQuantifier
def test_ops():
    uq = UncertaintyQuantifier()
    assert uq.stats() is not None