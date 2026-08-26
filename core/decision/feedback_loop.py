from dataclasses import dataclass
from typing import Optional


@dataclass
class ExecutionFeedback:
    action: str
    success: bool
    reward: float
    metadata: Optional[dict] = None


class FeedbackLoop:
    """Feeds execution outcomes back into adaptive decision systems."""

    def __init__(self, memory=None, policy=None):
        self.memory = memory
        self.policy = policy

    def process(self, feedback: ExecutionFeedback):
        if self.memory:
            self.memory.remember(
                {
                    "action": feedback.action,
                    "success": feedback.success,
                    "reward": feedback.reward,
                }
            )

        if self.policy and hasattr(self.policy, "update"):
            self.policy.update(feedback)

        return feedback
