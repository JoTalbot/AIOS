"""personalization test."""
def test(): from aios_core.personalization import PersonalizationEngine; s = PersonalizationEngine().stats(); assert isinstance(s, dict)
