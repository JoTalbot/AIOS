"""Emotional Intelligence for AIOS v10.8.0.

Emotion recognition from signals, regulation strategies,
empathy modeling, sentiment analysis, emotional state
tracking, conversation context awareness, and social
emotion contagion detection.

Classes:
    EmotionSignal   — recognized emotion signal
    EmotionState    — current emotional state vector
    EmotionalIntelligence — full emotional reasoning engine
"""

from __future__ import annotations

import logging
import math
import time
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Basic emotion categories (Ekman 6 + extensions)
EMOTION_CATEGORIES = {
    "joy": {"valence": 0.9, "arousal": 0.7, "dominance": 0.6},
    "sadness": {"valence": -0.7, "arousal": -0.3, "dominance": -0.5},
    "anger": {"valence": -0.8, "arousal": 0.8, "dominance": 0.7},
    "fear": {"valence": -0.6, "arousal": 0.7, "dominance": -0.6},
    "surprise": {"valence": 0.2, "arousal": 0.9, "dominance": 0.0},
    "disgust": {"valence": -0.8, "arousal": 0.3, "dominance": 0.4},
    "trust": {"valence": 0.7, "arousal": 0.2, "dominance": 0.5},
    "anticipation": {"valence": 0.3, "arousal": 0.6, "dominance": 0.4},
    "neutral": {"valence": 0.0, "arousal": 0.0, "dominance": 0.0},
}


@dataclass
class EmotionSignal:
    """Recognized emotion signal with confidence."""
    emotion: str
    confidence: float = 0.0
    source: str = "text"
    valence: float = 0.0  # -1..1 (negative..positive)
    arousal: float = 0.0  # 0..1 (calm..excited)
    dominance: float = 0.0  # -1..1 (submissive..dominant)
    timestamp: float = field(default_factory=time.time)


@dataclass
class EmotionState:
    """Current emotional state vector."""
    emotions: dict[str, float] = field(default_factory=lambda: {
        "joy": 0.0, "sadness": 0.0, "anger": 0.0,
        "fear": 0.0, "surprise": 0.0, "disgust": 0.0,
        "trust": 0.0, "anticipation": 0.0,
    })
    dominant_emotion: str = "neutral"
    valence: float = 0.0
    arousal: float = 0.0
    last_updated: float = field(default_factory=time.time)

    def intensity(self) -> float:
        """Overall emotional intensity."""
        return max(self.emotions.values()) if self.emotions else 0.0

    def valence_score(self) -> float:
        """Overall valence (positive vs negative)."""
        pos = self.emotions.get("joy", 0) + self.emotions.get("trust", 0)
        neg = self.emotions.get("sadness", 0) + self.emotions.get("anger", 0) + self.emotions.get("fear", 0)
        return pos - neg


class EmotionalIntelligence:
    """Full emotional reasoning engine.

    Features:
    - Emotion recognition from text/signal patterns
    - Emotional state tracking and updating
    - Regulation strategies (reappraisal, suppression, distraction)
    - Empathy modeling (perspective-taking)
    - Sentiment analysis (VAD model)
    - Emotional contagion detection
    - Conversation context awareness
    """

    def __init__(self) -> None:
        self.emotions: dict[str, float] = {
            "joy": 0.0, "sadness": 0.0, "anger": 0.0,
            "fear": 0.0, "surprise": 0.0, "disgust": 0.0,
        }
        # Override with emotion intensity values (initially all 0)
        self.emotion_state = EmotionState()
        self.vad_coords: dict[str, dict[str, float]] = dict(EMOTION_CATEGORIES)
        self.signals: list[EmotionSignal] = []
        self.regulation_history: list[dict[str, Any]] = []
        self.empathy_models: dict[str, dict[str, float]] = {}
        self._keyword_map: dict[str, list[str]] = {
            "joy": ["happy", "great", "wonderful", "excited", "love", "awesome", "pleased", "delighted"],
            "sadness": ["sad", "unhappy", "depressed", "miserable", "grief", "loss", "disappointed"],
            "anger": ["angry", "furious", "rage", "hate", "annoyed", "irritated", "mad", "frustrated"],
            "fear": ["scared", "afraid", "terrified", "worried", "anxious", "panic", "nervous"],
            "surprise": ["surprised", "amazed", "unexpected", "shocked", "astonished", "wow"],
            "disgust": ["disgusted", "revolted", "repulsed", "gross", "sick", "horrible", "awful"],
            "trust": ["trust", "reliable", "honest", "faithful", "loyal", "confident", "sure"],
            "anticipation": ["expect", "anticipate", "await", "hope", "look_forward", "predict"],
        }

    # ── Emotion Recognition ─────────────────────────────────────────

    def recognize_emotion(self, signals: dict[str, Any]) -> str:
        """Recognize dominant emotion from signals dict.

        Supports text-based keyword matching and numeric signal analysis.
        """
        # Check for explicit emotion specification first
        if "emotion" in signals:
            return signals["emotion"]

        text = signals.get("text", "")
        if isinstance(text, str) and text:
            return self._recognize_from_text(text)

        # Fallback: numeric signals (valence/arousal) or generic signal → neutral
        if "valence" not in signals and "arousal" not in signals:
            return signals.get("emotion", "neutral")

        valence = signals.get("valence", 0.0)
        arousal = signals.get("arousal", 0.0)

        best_emotion = "neutral"
        best_dist = float('inf')
        for emotion, coords in EMOTION_CATEGORIES.items():
            if emotion == "neutral":
                continue
            dist = math.sqrt((coords["valence"] - valence) ** 2 + (coords["arousal"] - arousal) ** 2)
            if dist < best_dist:
                best_dist = dist
                best_emotion = emotion

        return best_emotion

    def _recognize_from_text(self, text: str) -> str:
        """Recognize emotion from text using keyword matching."""
        text_lower = text.lower()
        scores: dict[str, int] = {}
        for emotion, keywords in self._keyword_map.items():
            count = sum(1 for kw in keywords if kw in text_lower)
            if count > 0:
                scores[emotion] = count

        if not scores:
            return "neutral"
        return max(scores, key=scores.get)

    def recognize_with_confidence(self, signals: dict[str, Any]) -> EmotionSignal:
        """Recognize emotion with confidence score."""
        emotion = self.recognize_emotion(signals)
        confidence = 0.5  # baseline

        text = signals.get("text", "")
        if isinstance(text, str) and text:
            text_lower = text.lower()
            keyword_count = sum(1 for kw in self._keyword_map.get(emotion, [])
                               if kw in text_lower)
            confidence = min(1.0, 0.3 + keyword_count * 0.2)

        coords = EMOTION_CATEGORIES.get(emotion, {"valence": 0.0, "arousal": 0.0, "dominance": 0.0})
        signal = EmotionSignal(
            emotion=emotion, confidence=round(confidence, 4),
            source=signals.get("source", "text"),
            valence=coords["valence"], arousal=coords["arousal"],
            dominance=coords["dominance"],
        )
        self.signals.append(signal)
        return signal

    # ── Emotion Regulation ──────────────────────────────────────────

    def regulate_emotion(self, emotion: str, intensity: float) -> dict[str, Any]:
        """Regulate an emotion using strategy selection."""
        intensity_val = max(0, min(1, intensity))
        self.emotion_state.emotions[emotion] = intensity_val
        # Also update the backward-compatible self.emotions dict
        if emotion in self.emotions:
            self.emotions[emotion] = intensity_val

        # Update state
        self.emotion_state.dominant_emotion = max(
            self.emotion_state.emotions, key=self.emotion_state.emotions.get
        )
        self.emotion_state.last_updated = time.time()

        # Select regulation strategy
        strategy = self._select_regulation_strategy(emotion, intensity)

        self.regulation_history.append({
            "emotion": emotion, "intensity": intensity,
            "strategy": strategy, "timestamp": time.time(),
        })

        return {"regulated": True, "emotion": emotion, "strategy": strategy}

    def _select_regulation_strategy(self, emotion: str, intensity: float) -> str:
        """Select best regulation strategy for an emotion."""
        if emotion in ("joy", "trust", "anticipation"):
            return "maintain" if intensity < 0.8 else "moderate"
        if emotion in ("sadness", "fear"):
            if intensity < 0.3:
                return "accept"
            if intensity < 0.6:
                return "reappraisal"
            return "distraction"
        if emotion == "anger":
            if intensity < 0.4:
                return "reappraisal"
            return "suppression"
        return "reappraisal"

    def apply_regulation(self, emotion: str, strategy: str) -> float:
        """Apply a regulation strategy and return new intensity."""
        current = self.emotion_state.emotions.get(emotion, 0.0)

        reduction = {
            "reappraisal": 0.3,
            "suppression": 0.2,
            "distraction": 0.4,
            "accept": 0.0,
            "maintain": 0.0,
            "moderate": 0.15,
        }.get(strategy, 0.2)

        new_intensity = max(0.0, current - reduction)
        self.emotion_state.emotions[emotion] = new_intensity
        return round(new_intensity, 4)

    # ── Empathy ────────────────────────────────────────────────────

    def model_empathy(self, target_id: str, target_emotion: str,
                      perspective: str = "cognitive") -> dict[str, Any]:
        """Model empathy toward another agent's emotional state."""
        self.empathy_models[target_id] = {
            "emotion": target_emotion,
            "perspective": perspective,
            "understanding_score": 0.7,
        }

        # Emotional empathy (shared feeling)
        if perspective == "emotional":
            contagion = self._compute_contagion(target_emotion)
            self.emotion_state.emotions[target_emotion] = min(
                1.0, self.emotion_state.emotions.get(target_emotion, 0.0) + contagion
            )

        return {
            "target": target_id,
            "emotion": target_emotion,
            "perspective": perspective,
            "understanding_score": self.empathy_models[target_id]["understanding_score"],
        }

    def _compute_contagion(self, emotion: str) -> float:
        """Compute emotional contagion factor."""
        high_contagion = {"joy", "sadness", "anger", "fear"}
        return 0.2 if emotion in high_contagion else 0.1

    # ── Sentiment Analysis ──────────────────────────────────────────

    def analyze_sentiment(self, text: str) -> dict[str, Any]:
        """Analyze sentiment of text using VAD (Valence-Arousal-Dominance)."""
        emotion = self._recognize_from_text(text)
        coords = EMOTION_CATEGORIES.get(emotion, {"valence": 0.0, "arousal": 0.0, "dominance": 0.0})
        return {
            "emotion": emotion,
            "valence": coords["valence"],
            "arousal": coords["arousal"],
            "dominance": coords["dominance"],
            "polarity": "positive" if coords["valence"] > 0.3 else
                        "negative" if coords["valence"] < -0.3 else "neutral",
        }

    # ── Stats ──────────────────────────────────────────────────────

    def stats(self) -> dict[str, Any]:
        """Return summary statistics."""
        return {
            "emotions_tracked": len(self.emotion_state.emotions),
            "signals_received": len(self.signals),
            "regulations_applied": len(self.regulation_history),
            "empathy_models": len(self.empathy_models),
            "dominant_emotion": self.emotion_state.dominant_emotion,
            "intensity": self.emotion_state.intensity(),
        }
