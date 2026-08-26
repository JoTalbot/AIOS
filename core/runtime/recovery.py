"""AIOS runtime recovery primitives."""

from dataclasses import dataclass


@dataclass
class RecoveryPolicy:
    max_retries: int = 3
    checkpoint_enabled: bool = True


class RecoveryManager:
    def __init__(self, policy: RecoveryPolicy | None = None):
        self.policy = policy or RecoveryPolicy()

    def should_retry(self, attempts: int) -> bool:
        return attempts < self.policy.max_retries
