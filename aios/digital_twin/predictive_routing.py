"""Route work using predicted node load without coupling to transport."""

from typing import Dict, Iterable, List


def rank_nodes(predicted_load: Dict[str, float], candidates: Iterable[str]) -> List[str]:
    """Return candidates ordered from lowest predicted load to highest."""
    return sorted(candidates, key=lambda node: predicted_load.get(node, float("inf")))
