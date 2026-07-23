"""Tests for emotional intelligence, theory of mind, and metacognition."""

from aios_core.emotional_intelligence import EmotionalIntelligence
from aios_core.theory_of_mind import TheoryOfMind
from aios_core.metacognition import MetacognitionEngine


def test_emotional_intelligence_stats():
    ei = EmotionalIntelligence()
    s = ei.stats()
    assert isinstance(s, dict)


def test_theory_of_mind_stats():
    tom = TheoryOfMind()
    s = tom.stats()
    assert isinstance(s, dict)


def test_metacognition_stats():
    mc = MetacognitionEngine()
    s = mc.stats()
    assert isinstance(s, dict)
