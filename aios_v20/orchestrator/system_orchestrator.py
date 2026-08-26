"""AIOS v20 System Orchestrator.

Coordinates workflow execution between governance, runtime and agents.
"""

from dataclasses import dataclass


@dataclass
class OrchestrationResult:
    status: str
    workflow_id: str
    message: str


class SystemOrchestrator:
    def __init__(self, workflow_controller=None, event_bus=None):
        self.workflow_controller = workflow_controller
        self.event_bus = event_bus

    def execute(self, workflow):
        if self.event_bus:
            self.event_bus.publish("workflow.started", {"id": workflow.id})

        if self.workflow_controller:
            self.workflow_controller.run(workflow)

        if self.event_bus:
            self.event_bus.publish("workflow.completed", {"id": workflow.id})

        return OrchestrationResult(
            status="completed",
            workflow_id=workflow.id,
            message="workflow executed"
        )
