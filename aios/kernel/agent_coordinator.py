"""AIOS v20.6 multi-agent coordinator."""


class AgentCoordinator:
    def __init__(self, graph, router):
        self.graph = graph
        self.router = router

    def assign(self, task_type: str):
        return self.router.route(task_type)
