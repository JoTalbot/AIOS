"""AIOS v20.6 task routing layer."""


class TaskRouter:
    def __init__(self, graph):
        self.graph = graph

    def route(self, task_type: str):
        for agent_id, agent in self.graph.agents.items():
            if getattr(agent, "role", None) == task_type:
                return agent
        return None
