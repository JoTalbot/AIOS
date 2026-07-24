"""Multi-Agent Reinforcement Learning for AIOS v10.8.0.

Multi-agent RL environment with cooperative/competitive
modes, shared reward, agent communication, policy
tracking, episode management, and team coordination.

Classes:
    AgentPolicy    — agent policy descriptor
    EpisodeResult  — episode outcome summary
    MultiAgentRL   — full multi-agent RL engine
"""

from __future__ import annotations

import logging
import random
import time
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class AgentPolicy:
    """Agent policy descriptor."""

    agent_id: str
    policy_type: str = "random"  # random, greedy, learned
    reward_total: float = 0.0
    actions_taken: int = 0
    cooperation_count: int = 0
    defection_count: int = 0
    last_action: str = ""


@dataclass
class EpisodeResult:
    """Episode outcome summary."""

    episode_id: int
    actions: dict[str, str]
    rewards: dict[str, float]
    shared_reward: float = 0.0
    cooperation_ratio: float = 0.0
    duration: float = 0.0
    timestamp: float = field(default_factory=time.time)


class MultiAgentRL:
    """Full multi-agent RL engine.

    Features:
    - Agent registration with policies
    - Cooperative/competitive environment step
    - Shared reward pool
    - Agent communication (message passing)
    - Policy tracking and statistics
    - Episode management
    - Team coordination metrics
    """

    def __init__(self, num_agents: int = 2, mode: str = "cooperative") -> None:
        self.num_agents = num_agents
        self.mode = mode  # cooperative or competitive
        self.agents: dict[str, AgentPolicy] = {}
        self.shared_reward = 0.0
        self.episodes: list[EpisodeResult] = []
        self.messages: list[dict[str, Any]] = []
        self._episode_counter = 0

    # ── Agent Registration ──────────────────────────────────────────

    def register_agent(self, agent_id: str, policy_type: str = "random") -> AgentPolicy:
        """Register an agent with a policy type."""
        policy = AgentPolicy(agent_id=agent_id, policy_type=policy_type)
        self.agents[agent_id] = policy
        return policy

    def remove_agent(self, agent_id: str) -> None:
        """Remove an agent."""
        self.agents.pop(agent_id, None)

    def get_agent(self, agent_id: str) -> AgentPolicy | None:
        """Return agent policy."""
        return self.agents.get(agent_id)

    # ── Environment Step ────────────────────────────────────────────

    def step(self, actions: dict[str, str]) -> dict[str, Any]:
        """Execute an environment step with agent actions."""
        rewards = {}

        for agent_id, action in actions.items():
            policy = self.agents.get(agent_id)
            if policy:
                policy.actions_taken += 1
                policy.last_action = action

                # Track cooperation/defection
                if action in ("cooperate", "share", "help"):
                    policy.cooperation_count += 1
                elif action in ("defect", "hoard", "attack"):
                    policy.defection_count += 1

        # Compute rewards based on mode
        if self.mode == "cooperative":
            # All agents benefit from cooperation
            coop_count = sum(
                1 for a in actions.values() if a in ("cooperate", "share", "help")
            )
            base_reward = 1.0 + coop_count * 0.5
            for agent_id in actions:
                rewards[agent_id] = base_reward
            self.shared_reward += base_reward
        else:
            # Competitive: relative performance
            for agent_id, action in actions.items():
                if action in ("cooperate", "share"):
                    rewards[agent_id] = random.uniform(0.3, 0.8)  # sucker's payoff
                elif action in ("defect", "attack"):
                    rewards[agent_id] = random.uniform(0.5, 1.2)  # temptation payoff
                else:
                    rewards[agent_id] = random.uniform(0.1, 0.5)

        # Update agent reward totals
        for agent_id, reward in rewards.items():
            policy = self.agents.get(agent_id)
            if policy:
                policy.reward_total += reward

        # Create episode result
        coop_ratio = (
            (
                sum(1 for a in actions.values() if a in ("cooperate", "share", "help"))
                / len(actions)
            )
            if actions
            else 0.0
        )

        result = EpisodeResult(
            episode_id=self._episode_counter,
            actions=actions,
            rewards=rewards,
            shared_reward=self.shared_reward,
            cooperation_ratio=round(coop_ratio, 4),
        )
        self.episodes.append(result)
        self._episode_counter += 1

        return {"rewards": rewards, "done": False, "episode_id": self._episode_counter}

    # ── Communication ──────────────────────────────────────────────

    def send_message(
        self, from_agent: str, to_agent: str, content: str, msg_type: str = "info"
    ) -> dict[str, Any]:
        """Send a message between agents."""
        msg = {
            "from": from_agent,
            "to": to_agent,
            "content": content,
            "type": msg_type,
            "timestamp": time.time(),
        }
        self.messages.append(msg)
        return msg

    def get_messages(self, agent_id: str, limit: int = 10) -> list[dict[str, Any]]:
        """Get messages for an agent."""
        relevant = [
            m for m in self.messages if m["to"] == agent_id or m["from"] == agent_id
        ]
        return relevant[-limit:]

    # ── Team Metrics ────────────────────────────────────────────────

    def cooperation_index(self) -> float:
        """Compute overall cooperation index across all agents."""
        if not self.agents:
            return 0.0
        coop = sum(a.cooperation_count for a in self.agents.values())
        total = sum(
            a.cooperation_count + a.defection_count for a in self.agents.values()
        )
        return coop / total if total > 0 else 0.0

    def avg_reward(self) -> float:
        """Average reward per agent."""
        if not self.agents:
            return 0.0
        return sum(a.reward_total for a in self.agents.values()) / len(self.agents)

    def best_agent(self) -> str | None:
        """Return agent with highest total reward."""
        if not self.agents:
            return None
        return max(self.agents.values(), key=lambda a: a.reward_total).agent_id

    # ── Stats ──────────────────────────────────────────────────────

    def stats(self) -> dict[str, Any]:
        """Return summary statistics."""
        return {
            "agents": len(self.agents),
            "mode": self.mode,
            "episodes": len(self.episodes),
            "shared_reward": round(self.shared_reward, 4),
            "avg_reward": round(self.avg_reward(), 4),
            "cooperation_index": round(self.cooperation_index(), 4),
            "messages": len(self.messages),
        }
