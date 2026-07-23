"""Cognitive deep scenario."""
from aios_core.emotional_intelligence import EmotionalIntelligence
from aios_core.theory_of_mind import TheoryOfMind
from aios_core.metacognition import MetacognitionEngine
from aios_core.social_intelligence import SocialIntelligence
from aios_core.creativity import CreativeEngine
from aios_core.personalization import PersonalizationEngine

def test_cognitive_stack():
    for s in [EmotionalIntelligence().stats(), TheoryOfMind().stats(),
              MetacognitionEngine().stats(), SocialIntelligence().stats(),
              CreativeEngine().stats(), PersonalizationEngine().stats()]:
        assert isinstance(s, dict)
