from typing import Any, Dict, List, Optional

class ContextManager:
    """Manages agent contexts including short-term memory, state, and history.

    Attributes:
        sessions: Dictionary storing agent contexts with agent_id as key.
    """

    def __init__(self) -> None:
        """Initialize ContextManager with empty sessions dictionary."""
        self.sessions: Dict[str, Dict[str, Any]] = {}

    def create(self, agent_id: str) -> None:
        """Create a new agent context with default empty structures.

        Args:
            agent_id: Unique identifier for the agent.
        """
        self.sessions[agent_id] = {
            "short_memory": [],
            "state": {},
            "history": []
        }

    def remember(self, agent_id: str, data: Any) -> None:
        """Add data to agent's history.

        Args:
            agent_id: Unique identifier for the agent.
            data: Information to be stored in history.
        """
        self.sessions[agent_id]["history"].append(data)

    def get(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve agent's context.

        Args:
            agent_id: Unique identifier for the agent.

        Returns:
            Agent's context dictionary or None if not found.
        """
        return self.sessions.get(agent_id)

    def get_summary(self) -> Dict[str, int]:
        """Get summary statistics of all agent sessions.

        Returns:
            Dictionary with counts of active sessions, total history entries,
            and total short memory entries across all agents.
        """
        total_history = sum(len(session["history"]) for session in self.sessions.values())
        total_short_memory = sum(len(session["short_memory"]) for session in self.sessions.values())
        return {
            "active_sessions": len(self.sessions),
            "total_history_entries": total_history,
            "total_short_memory_entries": total_short_memory
        }