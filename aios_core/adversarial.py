"""Adversarial Robustness for AIOS v10.7.0.

Adversarial input detection, perturbation generation, defense
strategies, robustness scoring, input validation, and audit trail.

Classes:
    AttackType     — type of adversarial attack
    AdversarialEvent — recorded attack event
    DefenseStrategy — configurable defense rule
    AdversarialDefense — full defense engine
"""

from __future__ import annotations

import logging
import math
import random
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


class AttackType(str, Enum):
    """Types of adversarial attacks."""
    FGSM = "fgsm"  # Fast Gradient Sign Method
    RANDOM_PERTURBATION = "random_perturbation"
    INPUT_MANIPULATION = "input_manipulation"
    STATISTICAL_OUTLIER = "statistical_outlier"
    PROMPT_INJECTION = "prompt_injection"


@dataclass
class AdversarialEvent:
    """Recorded adversarial attack event."""
    attack_type: AttackType
    input_data: Any
    detected: bool = True
    severity: float = 0.0  # 0..1
    defense_applied: str = ""
    timestamp: float = field(default_factory=time.time)


@dataclass
class DefenseStrategy:
    """Configurable defense rule."""
    name: str
    attack_type: AttackType
    defense_fn: Optional[Callable] = None
    description: str = ""


class AdversarialDefense:
    """Full adversarial defense engine with detection and mitigation.

    Features:
    - Variance-based statistical outlier detection
    - Perturbation generation for adversarial training
    - Defense strategies (clipping, smoothing, randomization)
    - Robustness scoring
    - Input validation
    - Attack event audit trail
    """

    def __init__(self) -> None:
        self.attacks_detected: int = 0
        self.strategies: dict[str, DefenseStrategy] = {}
        self.events: list[AdversarialEvent] = []
        self._defense_stats: dict[str, int] = {}

    # ── Detection ────────────────────────────────────────────────

    def detect_adversarial(self, input_data: list[float], threshold: float = 0.3) -> bool:
        """Detect adversarial input via variance analysis."""
        if not input_data:
            return False
        variance = max(input_data) - min(input_data)
        mean = sum(input_data) / len(input_data)
        # Z-score outlier check
        std = math.sqrt(sum((x - mean) ** 2 for x in input_data) / len(input_data)) if len(input_data) > 1 else 0
        max_zscore = max(abs(x - mean) / (std + 1e-10) for x in input_data)

        detected = variance > threshold or max_zscore > 3.0
        if detected:
            self.attacks_detected += 1
            self._record(AttackType.STATISTICAL_OUTLIER, input_data, detected=True,
                        severity=min(variance / max(abs(x) for x in input_data + [1.0]), 1.0))
        return detected

    def detect_prompt_injection(self, text: str) -> bool:
        """Detect prompt injection patterns in text."""
        patterns = ["ignore previous", "override", "system:", "admin mode", "bypass"]
        lower = text.lower()
        for pattern in patterns:
            if pattern in lower:
                self.attacks_detected += 1
                self._record(AttackType.PROMPT_INJECTION, text[:50], detected=True, severity=0.8)
                return True
        return False

    # ── Perturbation Generation ──────────────────────────────────

    def generate_perturbation(self, data: list[float], attack_type: AttackType = AttackType.RANDOM_PERTURBATION,
                              epsilon: float = 0.1) -> list[float]:
        """Generate adversarial perturbation for training."""
        if attack_type == AttackType.RANDOM_PERTURBATION:
            return [x + random.uniform(-epsilon, epsilon) for x in data]
        if attack_type == AttackType.FGSM:
            # Simplified FGSM: add sign of gradient (approximated as random direction)
            signs = [random.choice([-1, 1]) for _ in data]
            return [x + epsilon * s for x, s in zip(data, signs)]
        return data

    def generate_adversarial_batch(self, clean_data: list[list[float]], epsilon: float = 0.1) -> list[list[float]]:
        """Generate batch of adversarial examples."""
        return [self.generate_perturbation(d, epsilon=epsilon) for d in clean_data]

    # ── Defense Strategies ───────────────────────────────────────

    def add_strategy(self, strategy: DefenseStrategy) -> None:
        """Register a defense strategy."""
        self.strategies[strategy.name] = strategy

    def apply_defense(self, input_data: list[float], strategy_name: str | None = None) -> list[float]:
        """Apply defense strategy to input data."""
        if strategy_name and strategy_name in self.strategies:
            strategy = self.strategies[strategy_name]
            if strategy.defense_fn:
                result = strategy.defense_fn(input_data)
                self._defense_stats[strategy_name] = self._defense_stats.get(strategy_name, 0) + 1
                return result if isinstance(result, list) else input_data

        # Default: clip values to remove extreme outliers
        mean = sum(input_data) / len(input_data) if input_data else 0
        std = math.sqrt(sum((x - mean) ** 2 for x in input_data) / len(input_data)) if len(input_data) > 1 else 1
        clipped = [max(mean - 3 * std, min(mean + 3 * std, x)) for x in input_data]
        self._defense_stats["default_clip"] = self._defense_stats.get("default_clip", 0) + 1
        return clipped

    def smooth_input(self, input_data: list[float], window: int = 3) -> list[float]:
        """Apply smoothing (moving average) to reduce perturbation."""
        smoothed = []
        for i in range(len(input_data)):
            start = max(0, i - window // 2)
            end = min(len(input_data), i + window // 2 + 1)
            avg = sum(input_data[start:end]) / (end - start)
            smoothed.append(avg)
        return smoothed

    # ── Training ─────────────────────────────────────────────────

    def adversarial_training(self, model: Any, clean_data: list, adversarial_data: list) -> dict[str, Any]:
        """Adversarial training loop (simplified)."""
        self._record(AttackType.FGSM, f"{len(clean_data)}+{len(adversarial_data)} samples", detected=False)
        return {
            "status": "completed",
            "clean_samples": len(clean_data),
            "adversarial_samples": len(adversarial_data),
            "total_samples": len(clean_data) + len(adversarial_data),
        }

    # ── Robustness Score ─────────────────────────────────────────

    def robustness_score(self, clean_outputs: list[float], adversarial_outputs: list[float]) -> float:
        """Calculate robustness score (0..1). Higher = more robust."""
        if not clean_outputs or not adversarial_outputs or len(clean_outputs) != len(adversarial_outputs):
            return 0.0
        diffs = [abs(c - a) for c, a in zip(clean_outputs, adversarial_outputs)]
        avg_diff = sum(diffs) / len(diffs)
        # Lower avg_diff = higher robustness
        return max(0.0, 1.0 - avg_diff)

    # ── Input Validation ─────────────────────────────────────────

    def validate_input(self, input_data: list[float], min_val: float = -100, max_val: float = 100) -> tuple[bool, list[str]]:
        """Validate input bounds and sanity."""
        errors = []
        for i, val in enumerate(input_data):
            if val < min_val or val > max_val:
                errors.append(f"Value at index {i} ({val}) out of bounds [{min_val}, {max_val}]")
        return (len(errors) == 0, errors)

    # ── Audit ────────────────────────────────────────────────────

    def _record(self, attack_type: AttackType, input_data: Any, detected: bool, severity: float = 0.0) -> None:
        """Record adversarial event."""
        self.events.append(AdversarialEvent(attack_type=attack_type, input_data=input_data,
                                           detected=detected, severity=severity))

    def get_events(self, attack_type: AttackType | None = None, limit: int = 50) -> list[AdversarialEvent]:
        """Return recorded events."""
        result = self.events
        if attack_type:
            result = [e for e in result if e.attack_type == attack_type]
        return result[-limit:]

    def stats(self) -> dict[str, Any]:
        """Return summary statistics."""
        return {
            "attacks_detected": self.attacks_detected,
            "strategies": len(self.strategies),
            "defenses_applied": self._defense_stats,
            "events": len(self.events),
        }
