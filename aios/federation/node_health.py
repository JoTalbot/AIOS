from dataclasses import dataclass


@dataclass
class NodeHealth:
    node_id: str
    healthy: bool = True

    def update(self, status: bool) -> None:
        self.healthy = status
