"""AGI safety new."""
from aios_core.agi_safety import AGISafety
def test(): s=AGISafety().stats(); assert isinstance(s,dict)
