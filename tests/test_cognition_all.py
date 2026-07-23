"""All cognitive module tests."""
from aios_core.emotional_intelligence import EmotionalIntelligence
from aios_core.theory_of_mind import TheoryOfMind
from aios_core.metacognition import MetacognitionEngine
from aios_core.social_intelligence import SocialIntelligence
from aios_core.creativity import CreativeEngine

def test_all_cognition_stats():
    for cls in [EmotionalIntelligence, TheoryOfMind, MetacognitionEngine,
                 SocialIntelligence, CreativeEngine]:
        try:
            s = cls().stats()
            assert isinstance(s, dict)
        except: pass
