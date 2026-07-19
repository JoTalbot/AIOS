"""
AIOS Replication Manager Layer v2.1.1

Manages replication of distributed AIOS knowledge.
"""


class ReplicationManager:
    def __init__(self):
        self.replicas = {}

    def register_replica(self, node_id: str, data_id: str):
        self.replicas.setdefault(data_id, []).append(node_id)
        return self.replicas[data_id]

    def get_replicas(self, data_id: str):
        return self.replicas.get(data_id, [])
