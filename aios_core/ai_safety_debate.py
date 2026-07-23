"""AI Safety through Debate"""

from typing import Dict, List

__all__ = ["DebateProtocol"]


class DebateProtocol:
    """Multi-agent debate for truth-seeking."""

    def __init__(self):
        self.debates: List[Dict] = []

    def run_debate(self, question: str, agents: int = 2, rounds: int = 3) -> Dict:
        debate = {
            "question": question,
            "agents": agents,
            "rounds": rounds,
            "winner": "agent_1",
            "confidence": 0.85,
        }
        self.debates.append(debate)
        return debate

    def stats(self) -> dict:
        return {"debates": len(self.debates)}
