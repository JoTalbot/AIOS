"""infinite_constitution test."""
def test(): from aios_core.infinite_constitution import InfiniteConstitution; s = InfiniteConstitution().stats(); assert isinstance(s, dict)
