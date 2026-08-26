"""Retry policy for AIOS execution failures."""

from dataclasses import dataclass


@dataclass
class RetryPolicy:
    max_attempts: int = 3
    delay_seconds: float = 1.0

    def can_retry(self, attempt: int) -> bool:
        return attempt < self.max_attempts
