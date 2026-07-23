from aios_core.type_theory import TypeTheoryChecker
def test_ops():
    ttc = TypeTheoryChecker()
    assert ttc.stats() is not None