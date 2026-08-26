class RecoveryCluster:
    def __init__(self):
        self.nodes = {}

    def register(self, node_id, recovery_manager):
        self.nodes[node_id] = recovery_manager

    def recover_all(self):
        return {
            node: manager.recover()
            for node, manager in self.nodes.items()
        }
