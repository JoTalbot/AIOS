"""Emotional intelligence full."""
from aios_core.emotional_intelligence import EmotionalIntelligence
def test(): s=EmotionalIntelligence().stats(); assert isinstance(s,dict)
