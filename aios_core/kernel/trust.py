"""AIOS v20 trust management foundation."""


class TrustManager:
    def __init__(self):
        self._trust = {}

    def evaluate(self, agent_id: str) -> str:
        return self._trust.get(agent_id, "T0")

    def grant(self, agent_id: str, level: str = "T1") -> None:
        self._trust[agent_id] = level

    def revoke(self, agent_id: str) -> None:
        self._trust[agent_id] = "T0"
