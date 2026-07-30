"""AI Agent Swarm Auto-Scaling & Dynamic Role Allocator for AIOS v11.33.0.

Dynamically spawns, reassigns, and adjusts swarm agent roles based on workload characteristics.
"""

from __future__ import annotations

import time
from typing import Any

from .agent_swarm import AgentRole, AgentSwarm, SwarmAgent


class SwarmAutoScaler:
    """Dynamically scales swarm workers and reallocates roles based on pending workload."""

    def __init__(self, swarm: AgentSwarm | None = None) -> None:
        self.swarm = swarm
        self.autoscale_history: list[dict[str, Any]] = []

    def auto_scale_swarm_roles(
        self,
        pending_tasks: list[dict[str, Any]],
        swarm: AgentSwarm | None = None,
    ) -> dict[str, Any]:
        """Adjust swarm agent count and role distribution matching task demand."""
        target_swarm = swarm or self.swarm
        if target_swarm is None:
            return {"status": "error", "reason": "no swarm provided"}

        tasks_count = len(pending_tasks)
        workers_count = sum(1 for a in target_swarm.agents.values() if a.role == AgentRole.WORKER)

        spawned_count = 0
        # If workload is high (tasks_count > workers_count), spawn additional worker agents
        if tasks_count > workers_count:
            needed = tasks_count - workers_count
            for i in range(needed):
                new_agent = SwarmAgent(
                    id=f"auto_worker_{len(target_swarm.agents) + 1}",
                    name=f"Auto Worker {i + 1}",
                    role=AgentRole.WORKER,
                    capabilities=["all"],
                )
                target_swarm.add_agent(new_agent)
                spawned_count += 1

        result = {
            "pending_tasks": tasks_count,
            "workers_before": workers_count,
            "spawned_workers": spawned_count,
            "total_agents_after": len(target_swarm.agents),
            "timestamp": time.time(),
        }
        self.autoscale_history.append(result)
        return result
