"""Bounded execution engine for validated specialist graphs.

The engine deliberately accepts an injected executor. It schedules only roles whose
prerequisites have completed and never executes agents by itself.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from .execution_graph import ExecutionGraph


@dataclass(frozen=True)
class ExecutionResult:
    role: str
    success: bool
    error: str | None = None


class ExecutionEngine:
    """Execute a graph in dependency-safe batches with a hard agent bound."""

    def __init__(self, executor: Callable[[str], object], max_agents: int = 8) -> None:
        if max_agents < 1:
            raise ValueError("max_agents must be >= 1")
        self._executor = executor
        self._max_agents = max_agents

    def run(self, graph: ExecutionGraph) -> tuple[ExecutionResult, ...]:
        if len(graph.nodes) > self._max_agents:
            raise ValueError("execution graph exceeds agent budget")

        nodes = {node.role: node for node in graph.nodes}
        if len(nodes) != len(graph.nodes):
            raise ValueError("execution graph contains duplicate roles")

        completed: set[str] = set()
        results: list[ExecutionResult] = []
        remaining = set(nodes)

        while remaining:
            ready = sorted(
                role for role in remaining
                if set(nodes[role].depends_on).issubset(completed)
            )
            if not ready:
                raise ValueError("execution graph contains unresolved dependencies or a cycle")

            for role in ready:
                try:
                    self._executor(role)
                except Exception as exc:
                    results.append(ExecutionResult(role, False, str(exc)))
                    return tuple(results)
                results.append(ExecutionResult(role, True))
                completed.add(role)
                remaining.remove(role)

        return tuple(results)
