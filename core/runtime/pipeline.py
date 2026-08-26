"""AIOS end-to-end runtime pipeline orchestration."""

from dataclasses import dataclass, field
from typing import Any, Dict


@dataclass
class PipelineContext:
    goal: str
    state: str = "created"
    metadata: Dict[str, Any] = field(default_factory=dict)


class RuntimePipeline:
    """Coordinates planner, decision and execution lifecycle hooks."""

    def __init__(self, planner=None, decision_runtime=None):
        self.planner = planner
        self.decision_runtime = decision_runtime

    def initialize(self, goal: str) -> PipelineContext:
        context = PipelineContext(goal=goal)

        if self.planner:
            context.metadata["plan"] = self.planner.create_plan(goal)

        context.state = "planned"
        return context

    def decide(self, context: PipelineContext):
        if not self.decision_runtime:
            context.state = "ready"
            return None

        decision = self.decision_runtime.evaluate(context)
        context.metadata["decision"] = decision
        context.state = "decided"
        return decision

    def complete(self, context: PipelineContext):
        context.state = "completed"
        return context
