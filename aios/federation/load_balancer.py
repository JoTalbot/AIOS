from dataclasses import dataclass


@dataclass
class LoadBalancer:
    """Federation task distribution primitive."""

    def select_node(self, nodes: list[str]) -> str | None:
        if not nodes:
            return None
        return nodes[0]
