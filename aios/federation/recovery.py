class FaultRecoveryManager:
    def __init__(self):
        self.failed_nodes = []

    def detect_failure(self, node_id: str):
        self.failed_nodes.append(node_id)
        return node_id

    def redistribute_tasks(self, nodes):
        return [n for n in nodes if n not in self.failed_nodes]

    def recover(self, node_id: str):
        if node_id in self.failed_nodes:
            self.failed_nodes.remove(node_id)
            return True
        return False
