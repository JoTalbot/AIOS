"""Self-Healing System for AIOS"""

import logging
from typing import Callable, Dict, Optional

__all__ = ["SelfHealing"]

logger = logging.getLogger(__name__)


class SelfHealing:
    """Automatic recovery from failures.

    Maintains a registry of error-type → recovery strategy mappings
    and attempts automatic healing when a registered failure type is detected.
    """

    def __init__(self):
        self.recovery_strategies: Dict[str, Callable] = {}

    def register_strategy(self, error_type: str, strategy: Callable) -> None:
        """Register a recovery strategy for a given error type name.

        Args:
            error_type: The ``__name__`` of the exception class (e.g. ``"ConnectionError"``).
            strategy: A callable that receives a context dict and performs recovery.
        """
        self.recovery_strategies[error_type] = strategy

    def heal(self, error: Exception, context: Optional[Dict] = None) -> bool:
        """Attempt to heal from a failure by invoking the registered strategy.

        Args:
            error: The exception that triggered the healing attempt.
            context: Optional dictionary with contextual information for the strategy.

        Returns:
            ``True`` if a strategy was found and executed successfully, ``False`` otherwise.
        """
        error_type = type(error).__name__
        if error_type in self.recovery_strategies:
            try:
                self.recovery_strategies[error_type](context or {})
                return True
            except Exception as exc:
                logger.error(
                    "Recovery strategy for %s failed: %s", error_type, exc
                )
                return False
        return False

    def stats(self) -> dict:
        """Return statistics about registered recovery strategies."""
        return {"strategies": len(self.recovery_strategies)}
