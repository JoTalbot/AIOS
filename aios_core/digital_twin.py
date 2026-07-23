"""Digital Twin for AIOS"""

from typing import Any, Dict


class DigitalTwin:
    """Digital twin of an AIOS instance or agent."""

    def __init__(self, twin_id: str, real_entity: str):
        self.twin_id = twin_id
        self.real_entity = real_entity
        self.state: Dict[str, Any] = {}
        self.history: list = []

    def sync(self, new_state: Dict):
        self.history.append(self.state.copy())
        self.state.update(new_state)

    def simulate(self, action: str) -> Dict:
        return {
            "twin_id": self.twin_id,
            "action": action,
            "predicted_outcome": "success",
        }

    def stats(self) -> dict:
        return {
            "id": self.twin_id,
            "entity": self.real_entity,
            "history_length": len(self.history),
        }
