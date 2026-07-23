"""Theory of mind full."""
from aios_core.theory_of_mind import TheoryOfMind
def test(): s=TheoryOfMind().stats(); assert isinstance(s,dict)
