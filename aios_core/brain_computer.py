"""Brain-Computer Interface Abstraction for AIOS v10.9.0.

BCI interface with signal acquisition, intent
decoding, signal processing, neural command
mapping, adaptive filtering, and session management.

Classes:
    BCISession     — BCI session state
    BCIInterface   — full BCI engine
"""

from __future__ import annotations

import logging
import math
import random
import time
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class BCISession:
    """BCI session state."""
    connected: bool = False
    started_at: float = 0.0
    signals_read: int = 0
    intents_decoded: int = 0


class BCIInterface:
    """Full Brain-Computer Interface engine.

    Features:
    - Connection management
    - EEG signal simulation and processing
    - Intent decoding from neural signals
    - Neural command mapping
    - Adaptive signal filtering
    - Session tracking
    """

    def __init__(self, channels: int = 64, sample_rate: float = 250.0) -> None:
        self.connected = False
        self.channels = channels
        self.sample_rate = sample_rate
        self.signals: list[dict[str, Any]] = []
        self._command_map: dict[str, str] = {
            "move_forward": "up",
            "stop": "stop",
            "turn_left": "left",
            "turn_right": "right",
            "select": "select",
        }
        self._session = BCISession()
        self._filter_history: list[dict[str, Any]] = []

    def connect(self) -> dict[str, Any]:
        """Connect to BCI device (backward-compatible)."""
        self.connected = True
        self._session.connected = True
        self._session.started_at = time.time()
        return {"status": "connected", "channels": self.channels}

    def disconnect(self) -> None:
        """Disconnect from BCI device."""
        self.connected = False
        self._session.connected = False

    def read_signal(self) -> dict[str, Any]:
        """Read neural signal (backward-compatible)."""
        if not self.connected:
            return {"error": "Not connected"}

        # Simulate EEG signal with realistic noise patterns
        sample = [random.gauss(0, 0.1) for _ in range(self.channels)]
        # Add alpha wave (8-12 Hz) component
        alpha_freq = random.uniform(8, 12)
        t = time.time() * self.sample_rate
        for i in range(self.channels):
            sample[i] += 0.3 * math.sin(2 * math.pi * alpha_freq * i / self.channels)

        signal = {
            "type": "eeg",
            "channels": self.channels,
            "sample_rate": self.sample_rate,
            "sample": sample,
            "timestamp": time.time(),
        }
        self.signals.append(signal)
        self._session.signals_read += 1
        return signal

    def decode_intent(self, signal: dict[str, Any]) -> str:
        """Decode intent from neural signal (backward-compatible)."""
        sample = signal.get("sample", [])
        if not sample:
            return "unknown"

        # Compute signal features
        avg = sum(sample) / len(sample) if sample else 0
        variance = sum((s - avg) ** 2 for s in sample) / len(sample) if sample else 0

        # Map signal patterns to intents
        if avg > 0.5:
            return "move_forward"
        elif avg < -0.5:
            return "stop"
        elif variance > 0.2:
            return "select"
        else:
            return "observe"

    def map_command(self, intent: str) -> str:
        """Map decoded intent to system command."""
        return self._command_map.get(intent, "unknown")

    def filter_signal(self, signal: dict[str, Any], cutoff: float = 0.05) -> dict[str, Any]:
        """Apply adaptive filter to signal."""
        sample = signal.get("sample", [])
        # Low-pass filter: remove high-frequency noise
        filtered = [s if abs(s) < cutoff else 0.0 for s in sample]
        self._filter_history.append({"cutoff": cutoff, "filtered_count": len(filtered)})
        return {**signal, "sample": filtered, "filtered": True}

    def batch_decode(self, num_signals: int = 5) -> list[str]:
        """Read and decode multiple signals."""
        intents = []
        for _ in range(num_signals):
            signal = self.read_signal()
            intent = self.decode_intent(signal)
            intents.append(intent)
            self._session.intents_decoded += 1
        return intents

    def stats(self) -> dict[str, Any]:
        """Return summary statistics."""
        return {
            "connected": self.connected,
            "signals": len(self.signals),
            "channels": self.channels,
            "session_signals": self._session.signals_read,
            "session_intents": self._session.intents_decoded,
        }
