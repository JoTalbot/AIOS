"""theory_of_mind test."""
def test(): from aios_core.theory_of_mind import TheoryOfMind; s = TheoryOfMind().stats(); assert isinstance(s, dict)
