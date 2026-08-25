"""AIOS v20 trust management foundation."""

VALID_TRUST_LEVELS = frozenset({"T0", "T1", "T2", "T3"})


class TrustManager:
    """Keep the current bounded trust level for each registered agent ID."""

    def __init__(self) -> None:
        self._trust: dict[str, str] = {}

    def evaluate(self, agent_id: str) -> str:
        """Return current trust, defaulting to untrusted T0."""
        return self._trust.get(agent_id, "T0")

    def grant(self, agent_id: str, level: str = "T1") -> None:
        """Set a validated trust level for an agent."""
        if level not in VALID_TRUST_LEVELS:
            raise ValueError(f"unknown trust level: {level}")
        self._trust[agent_id] = level

    def revoke(self, agent_id: str) -> None:
        """Return an agent to the untrusted T0 level."""
        self._trust[agent_id] = "T0"
