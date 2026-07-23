"""personalization test."""
from aios_core.personalization import PersonalizationEngine
def test_init(): s = PersonalizationEngine().stats(); assert isinstance(s, dict)
