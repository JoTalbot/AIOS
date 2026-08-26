from dataclasses import dataclass
from typing import Iterable


@dataclass
class ConsensusEngine:
    """Minimal federation decision coordinator."""

    def choose(self, candidates: Iterable[str]) -> str | None:
        items = list(candidates)
        return items[0] if items else None
