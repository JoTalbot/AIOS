"""AIOS controlled improvement proposals."""

from dataclasses import dataclass


@dataclass
class ImprovementProposal:
    component: str
    change: str
    approved: bool = False


class ImprovementEngine:
    def propose(self, component: str, change: str) -> ImprovementProposal:
        return ImprovementProposal(component, change)
