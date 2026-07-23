"""Workflow Engine for AIOS"""

from typing import List, Dict, Any, Callable
from dataclasses import dataclass, field
import uuid


@dataclass
class WorkflowStep:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str
    action: Callable
    params: Dict = field(default_factory=dict)


@dataclass
class Workflow:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str
    steps: List[WorkflowStep] = field(default_factory=list)
    status: str = "pending"


class WorkflowEngine:
    """Simple workflow orchestration engine."""

    def __init__(self):
        self.workflows: Dict[str, Workflow] = {}

    def create_workflow(self, name: str) -> Workflow:
        wf = Workflow(name=name)
        self.workflows[wf.id] = wf
        return wf

    def add_step(self, workflow_id: str, name: str, action: Callable, **params):
        wf = self.workflows[workflow_id]
        step = WorkflowStep(name=name, action=action, params=params)
        wf.steps.append(step)
        return step

    def execute(self, workflow_id: str) -> Dict:
        wf = self.workflows[workflow_id]
        wf.status = "running"
        results = []

        for step in wf.steps:
            try:
                result = step.action(**step.params)
                results.append({"step": step.name, "result": result})
            except Exception as e:
                wf.status = "failed"
                return {"status": "failed", "error": str(e)}

        wf.status = "completed"
        return {"status": "completed", "results": results}

    def stats(self) -> dict:
        return {
            "total_workflows": len(self.workflows),
            "by_status": {
                status: sum(1 for w in self.workflows.values() if w.status == status)
                for status in ["pending", "running", "completed", "failed"]
            },
        }


workflow_engine = WorkflowEngine()
