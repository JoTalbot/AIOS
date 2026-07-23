"""Type theory full ops."""
from aios_core.type_theory import TypeTheoryChecker
def test_ttc(): s=TypeTheoryChecker().stats(); assert isinstance(s,dict)
