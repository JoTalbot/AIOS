"""test_cognitive_scenario test."""
from aios_core.theory_of_mind import TheoryOfMind
from aios_core.emotional_intelligence import EmotionalIntelligence
from aios_core.metacognition import MetacognitionEngine
from aios_core.social_intelligence import SocialIntelligence

def test_cognitive():
    for cls in [TheoryOfMind, EmotionalIntelligence, MetacognitionEngine, SocialIntelligence]:
        s = cls().stats()
        assert isinstance(s, dict)

