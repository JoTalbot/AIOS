"""
AIOS Memory Federation Layer v2.1.1

Controls distributed memory synchronization according to constitutional rules.
"""


class MemoryFederation:
    def __init__(self):
        self.nodes = []

    def register_memory_node(self, node_id: str, policy: str):
        self.nodes.append({
            "node_id": node_id,
            "policy": policy
        })
        return self.nodes[-1]

    def sync_allowed(self, memory_type: str) -> bool:
        return memory_type in ["operational", "constitutional"]
