from dataclasses import dataclass


@dataclass
class WorkflowState:
    name: str
    status: str


class AutonomousWorkflowController:
    def __init__(self):
        self.state = WorkflowState('workflow', 'IDLE')

    def start(self, goal):
        self.state = WorkflowState(goal, 'RUNNING')
        return self.state

    def complete(self):
        self.state.status = 'COMPLETED'
        return self.state
