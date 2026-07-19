"""
AIOS Workflow Engine Layer v2.1.1

Manages AIOS workflows and execution chains.
"""


class WorkflowEngine:
    def __init__(self):
        self.workflows = []

    def create(self, workflow: dict):
        self.workflows.append(workflow)
        return workflow

    def list_workflows(self):
        return self.workflows
