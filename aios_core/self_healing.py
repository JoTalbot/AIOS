"""Self-Healing System for AIOS"""

from typing import Callable, Dict


class SelfHealing:
    """Automatic recovery from failures."""

    def __init__(self):
        self.recovery_strategies: Dict[str, Callable] = {}

    def register_strategy(self, error_type: str, strategy: Callable):
        self.recovery_strategies[error_type] = strategy

    def heal(self, error: Exception, context: Dict = None) -> bool:
        error_type = type(error).__name__
        if error_type in self.recovery_strategies:
            try:
                self.recovery_strategies[error_type](context or {})
                return True
            except:
                return False
        return False

    def stats(self) -> dict:
        return {"strategies": len(self.recovery_strategies)}