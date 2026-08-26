"""Production error recovery coordination layer."""

from dataclasses import dataclass


@dataclass
class RecoveryResult:
    recovered: bool
    reason: str = ""


class ProductionErrorRecovery:
    def recover(self, error: Exception) -> RecoveryResult:
        return RecoveryResult(recovered=False, reason=str(error))
