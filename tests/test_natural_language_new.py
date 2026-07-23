"""natural_language test."""
def test(): from aios_core.natural_language import NLProcessor; s = NLProcessor().stats(); assert isinstance(s, dict)
