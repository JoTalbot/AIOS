"""Brain-Computer Interface Abstraction for AIOS"""

from typing import Dict, List


class BCIInterface:
    """Abstract Brain-Computer Interface."""

    def __init__(self):
        self.connected = False
        self.signals: List[Dict] = []

    def connect(self):
        self.connected = True
        return {"status": "connected"}

    def read_signal(self) -> Dict:
        if not self.connected:
            return {"error": "Not connected"}
        signal = {"type": "eeg", "channels": 64, "sample": [0.1] * 64}
        self.signals.append(signal)
        return signal

    def decode_intent(self, signal: Dict) -> str:
        return "move_forward" if sum(signal.get("sample", [])) > 0 else "stop"

    def stats(self) -> dict:
        return {"connected": self.connected, "signals": len(self.signals)}