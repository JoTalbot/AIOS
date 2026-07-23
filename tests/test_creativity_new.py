"""creativity test."""
def test(): from aios_core.creativity import CreativeEngine; s = CreativeEngine().stats(); assert isinstance(s, dict)
