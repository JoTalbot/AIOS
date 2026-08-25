"""Dependency report generator foundation.

Creates structured reports from module dependency analysis.
"""

from dataclasses import dataclass, asdict
from typing import Dict, List


@dataclass
class DependencyReport:
    modules: int
    edges: int
    cycles: List[List[str]]
    hotspots: List[str]


class DependencyReportGenerator:
    def generate(self, graph: Dict[str, List[str]], cycles: List[List[str]] | None = None) -> DependencyReport:
        cycles = cycles or []
        incoming = {module: 0 for module in graph}

        for dependencies in graph.values():
            for dependency in dependencies:
                if dependency in incoming:
                    incoming[dependency] += 1

        hotspots = sorted(incoming, key=incoming.get, reverse=True)[:10]

        return DependencyReport(
            modules=len(graph),
            edges=sum(len(items) for items in graph.values()),
            cycles=cycles,
            hotspots=hotspots,
        )

    def to_dict(self, report: DependencyReport) -> dict:
        return asdict(report)
