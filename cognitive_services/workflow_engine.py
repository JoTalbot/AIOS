"""AIOS v22.2 Cognitive Workflow Engine foundation.

Provides a minimal orchestration layer for Goal -> Context -> Reasoning -> Action
pipelines while keeping runtime isolation.
"""


class CognitiveWorkflowEngine:
    def __init__(self, registry=None):
        self.registry = registry
        self.steps = []

    def add_step(self, name, handler):
        self.steps.append((name, handler))

    def execute(self, payload):
        state = payload
        for _, handler in self.steps:
            state = handler(state)
        return state

    def health(self):
        return {"status": "ok", "steps": len(self.steps)}
