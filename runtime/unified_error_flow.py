"""Unified error flow foundation for AIOS runtime."""

from dataclasses import dataclass


@dataclass
class RuntimeErrorEvent:
    stage: str
    message: str
    recovered: bool = False


class UnifiedErrorFlow:
    def handle(self, stage: str, message: str) -> RuntimeErrorEvent:
        return RuntimeErrorEvent(stage=stage, message=message)
