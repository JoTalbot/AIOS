"""Agent Runtime Orchestrator.

Coordinates workflow execution across specialized agents.
"""


class AgentRuntimeOrchestrator:
    def __init__(self, workflow=None, bus=None):
        self.workflow = workflow
        self.bus = bus

    def attach_workflow(self, workflow):
        self.workflow = workflow

    def attach_bus(self, bus):
        self.bus = bus

    def execute(self, context):
        if self.workflow is None:
            return {"status": "no_workflow"}

        return self.workflow.run(context)
