from dataclasses import dataclass
from typing import Any


@dataclass
class LearningEvent:
    task_id: str
    action: str
    success: bool
    reward: float = 0.0


class LearningIntegration:
    """Connect runtime execution results with the learning loop."""

    def __init__(self, feedback_loop):
        self.feedback_loop = feedback_loop

    def process_result(self, event: LearningEvent) -> Any:
        return self.feedback_loop.record(
            action=event.action,
            success=event.success,
            reward=event.reward,
            metadata={"task_id": event.task_id},
        )
