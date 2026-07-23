"""Personalization full."""
from aios_core.personalization import PersonalizationEngine
def test(): s=PersonalizationEngine().stats(); assert isinstance(s,dict)
