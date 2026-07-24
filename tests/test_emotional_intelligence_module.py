"""Tests for aios_core/emotional_intelligence.py"""
from __future__ import annotations
import pytest
from aios_core.emotional_intelligence import EmotionalIntelligence, EmotionState, EmotionSignal


@pytest.fixture()
def ei():
    return EmotionalIntelligence()


class TestEmotionState:
    def test_create(self):
        e = EmotionState(emotions={"happy": 0.9})
        assert isinstance(e.emotions, dict)

    def test_valence(self):
        e = EmotionState(emotions={"happy": 0.9})
        assert isinstance(e.valence, (int, float))


class TestEmotionalIntelligence:
    def test_create(self, ei):
        assert ei is not None

    def test_recognize_emotion(self, ei):
        result = ei.recognize_emotion(signals={"text": "I am so happy today!"})
        assert result is not None

    def test_recognize_with_confidence(self, ei):
        result = ei.recognize_with_confidence(signals={"text": "This is terrible"})
        assert result is not None

    def test_analyze_sentiment(self, ei):
        result = ei.analyze_sentiment(text="Great product, love it!")
        assert isinstance(result, (str, dict, float))

    def test_regulate_emotion(self, ei):
        result = ei.regulate_emotion(emotion="angry", intensity=0.8)
        assert isinstance(result, (str, dict))

    def test_model_empathy(self, ei):
        result = ei.model_empathy(target_id="user1", target_emotion="sad")
        assert isinstance(result, (str, dict))

    def test_stats(self, ei):
        s = ei.stats()
        assert isinstance(s, dict)
