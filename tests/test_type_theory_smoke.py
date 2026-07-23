"""type_theory smoke test."""
def test_ttc(): from aios_core.type_theory import TypeTheoryChecker; assert TypeTheoryChecker().stats() is not None
