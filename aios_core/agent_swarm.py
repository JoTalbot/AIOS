"""Multi-Agent Swarm System for AIOS v10.7.0.

Swarm of collaborative agents with voting, leader election,
task assignment, consensus protocols, shared memory, and
swarm metrics.

Classes:
    SwarmAgent     — individual agent in the swarm
    SwarmMessage   — inter-agent communication message
    SwarmDecision  — collective decision with voting results
    AgentSwarm     — full swarm system (no dependency on AdvancedAgent)
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

logger = logging.getLogger(__name__)


class AgentRole(StrEnum):
    """Agent role in swarm."""

    LEADER = "leader"
    WORKER = "worker"
    OBSERVER = "observer"
    COORDINATOR = "coordinator"


@dataclass
class SwarmAgent:
    """Individual agent in the swarm."""

    id: str = ""
    name: str = ""
    role: AgentRole = AgentRole.WORKER
    capabilities: list[str] = field(default_factory=list)
    reputation: float = 1.0  # 0..5
    memory: dict[str, Any] = field(default_factory=dict)
    current_task: str | None = None
    active: bool = True

    def __post_init__(self) -> None:
        if not self.id:
            import uuid

            self.id = str(uuid.uuid4())[:8]


@dataclass
class SwarmMessage:
    """Inter-agent communication message."""

    from_id: str
    to_id: str | None = None  # None = broadcast
    content: dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


@dataclass
class SwarmDecision:
    """Collective decision with voting results."""

    topic: str
    decision: str = "pending"
    votes: dict[str, str] = field(default_factory=dict)  # agent_id → vote
    majority: str = ""
    confidence: float = 0.0
    timestamp: float = field(default_factory=time.time)


class AgentSwarm:
    """Full swarm system with voting, task assignment, and consensus.

    Features:
    - Agent registration with roles and capabilities
    - Inter-agent messaging (direct + broadcast)
    - Voting-based collective decisions
    - Leader election
    - Capability-based task assignment
    - Shared memory space
    - Swarm metrics
    """

    def __init__(self, name: str) -> None:
        self.name = name
        self.agents: dict[str, SwarmAgent] = {}
        self.shared_memory: dict[str, Any] = {}
        self.messages: list[SwarmMessage] = []
        self.decisions: list[SwarmDecision] = []
        self._leader_id: str | None = None

    # ── Agent Management ────────────────────────────────────────

    def add_agent(self, agent: SwarmAgent) -> None:
        """Add an agent to the swarm."""
        self.agents[agent.id] = agent

    def remove_agent(self, agent_id: str) -> None:
        """Remove an agent."""
        del self.agents[agent_id]
        if self._leader_id == agent_id:
            self._leader_id = None

    def get_agent(self, agent_id: str) -> SwarmAgent | None:
        """Return agent by ID."""
        return self.agents.get(agent_id)

    # ── Messaging ────────────────────────────────────────────────

    def send_message(
        self, from_id: str, to_id: str | None, content: dict[str, Any]
    ) -> SwarmMessage:
        """Send message (direct or broadcast)."""
        msg = SwarmMessage(from_id=from_id, to_id=to_id, content=content)
        self.messages.append(msg)
        if to_id is None:
            # Broadcast to all
            for agent in self.agents.values():
                agent.memory[f"msg_{len(self.messages)}"] = content
        else:
            target = self.agents.get(to_id)
            if target:
                target.memory[f"msg_{len(self.messages)}"] = content
        return msg

    def broadcast(self, message: dict[str, Any]) -> None:
        """Broadcast a message to all agents."""
        self.send_message("system", None, message)

    def get_messages(
        self, agent_id: str | None = None, limit: int = 50
    ) -> list[SwarmMessage]:
        """Get messages for an agent or all."""
        if agent_id:
            return [m for m in self.messages if m.to_id == agent_id or m.to_id is None][
                -limit:
            ]
        return self.messages[-limit:]

    # ── Collective Decisions ─────────────────────────────────────

    def collective_decision(
        self, topic: str, options: list[str] | None = None
    ) -> SwarmDecision:
        """Make a collective decision via voting."""
        options = options or ["approve", "reject"]
        decision = SwarmDecision(topic=topic)

        # Each agent votes based on reputation-weighted preference
        for agent in self.agents.values():
            if not agent.active:
                continue
            # Simple heuristic: high reputation → approve, low → reject
            vote = "approve" if agent.reputation >= 2.0 else "reject"
            if options and vote not in options:
                vote = options[0]
            decision.votes[agent.id] = vote

        # Determine majority
        vote_counts: dict[str, int] = {}
        for v in decision.votes.values():
            vote_counts[v] = vote_counts.get(v, 0) + 1
        if vote_counts:
            decision.majority = max(vote_counts, key=vote_counts.get)
            total = sum(vote_counts.values())
            decision.confidence = (
                vote_counts[decision.majority] / total if total > 0 else 0.0
            )

        decision.decision = decision.majority
        self.decisions.append(decision)
        return decision

    def vote(self, topic: str, agent_votes: dict[str, str]) -> SwarmDecision:
        """Submit explicit votes from agents."""
        decision = SwarmDecision(topic=topic, votes=agent_votes)
        vote_counts: dict[str, int] = {}
        for v in agent_votes.values():
            vote_counts[v] = vote_counts.get(v, 0) + 1
        if vote_counts:
            decision.majority = max(vote_counts, key=vote_counts.get)
            decision.confidence = (
                vote_counts[decision.majority] / len(agent_votes)
                if agent_votes
                else 0.0
            )
        decision.decision = decision.majority
        self.decisions.append(decision)
        return decision

    # ── Leader Election ──────────────────────────────────────────

    def elect_leader(self) -> SwarmAgent | None:
        """Elect leader based on highest reputation."""
        active = [a for a in self.agents.values() if a.active]
        if not active:
            return None
        leader = max(active, key=lambda a: a.reputation)
        leader.role = AgentRole.LEADER
        self._leader_id = leader.id
        # Reset other leaders
        for a in self.agents.values():
            if a.id != leader.id and a.role == AgentRole.LEADER:
                a.role = AgentRole.WORKER
        return leader

    def get_leader(self) -> SwarmAgent | None:
        """Return current leader."""
        if self._leader_id:
            return self.agents.get(self._leader_id)
        return None

    # ── Task Assignment ──────────────────────────────────────────

    def assign_task(
        self, task_name: str, required_capability: str
    ) -> SwarmAgent | None:
        """Assign task to best-fit agent by capability."""
        candidates = [
            a
            for a in self.agents.values()
            if a.active
            and a.current_task is None
            and required_capability in a.capabilities
        ]
        if not candidates:
            return None
        best = max(candidates, key=lambda a: a.reputation)
        best.current_task = task_name
        return best

    def complete_task(self, agent_id: str) -> None:
        """Mark agent's current task as completed."""
        agent = self.agents.get(agent_id)
        if agent:
            agent.current_task = None
            agent.reputation = min(agent.reputation + 0.1, 5.0)

    def fail_task(self, agent_id: str) -> None:
        """Mark agent's current task as failed."""
        agent = self.agents.get(agent_id)
        if agent:
            agent.current_task = None
            agent.reputation = max(agent.reputation - 0.2, 0.0)

    # ── Shared Memory ────────────────────────────────────────────

    def store_shared(self, key: str, value: Any) -> None:
        """Store value in shared memory."""
        self.shared_memory[key] = value

    def get_shared(self, key: str) -> Any:
        """Get value from shared memory."""
        return self.shared_memory.get(key)

    # ── Stats ────────────────────────────────────────────────────

    def stats(self) -> dict[str, Any]:
        """Return summary statistics."""
        active = sum(1 for a in self.agents.values() if a.active)
        by_role: dict[str, int] = {}
        for a in self.agents.values():
            by_role[a.role.value] = by_role.get(a.role.value, 0) + 1
        return {
            "agents": len(self.agents),
            "active_agents": active,
            "by_role": by_role,
            "shared_memory": len(self.shared_memory),
            "decisions": len(self.decisions),
            "messages": len(self.messages),
            "leader": self._leader_id,
        }
