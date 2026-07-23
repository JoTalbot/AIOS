"""World Model / World Simulator for AIOS"""

from typing import Any, Dict, List


class WorldModel:
    """Learns and simulates environment dynamics."""

    def __init__(self):
        self.dynamics_model: Dict = {}
        self.observations: List[Dict] = []

    def observe(self, state: Dict, action: Any, next_state: Dict, reward: float) -> None:
        """Execute observe."""
        self.observations.append(
            {
                "state": state,
                "action": action,
                "next_state": next_state,
                "reward": reward,
            }
        )

    def predict(self, state: Dict, action: Any) -> Dict:
        """Execute predict."""
        # Simple linear dynamics
        return {k: v * 0.9 for k, v in state.items()}

    def imagine(self, horizon: int = 10) -> List[Dict]:
        """Execute imagine."""
        trajectory = []
        state = {"x": 0.0}
        for _ in range(horizon):
            action = "noop"
            next_state = self.predict(state, action)
            trajectory.append({"state": state, "action": action, "next": next_state})
            state = next_state
        return trajectory

    def stats(self) -> dict:
        """Return statistics dict."""
        return {"observations": len(self.observations)}
