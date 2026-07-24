"""Feature Flags for AIOS"""

from typing import Dict


class FeatureFlags:
    """Simple feature flag system."""

    def __init__(self):
        """Initialize FeatureFlags."""
        self.flags: dict[str, bool] = {}

    def enable(self, flag: str) -> None:
        """Execute enable."""
        self.flags[flag] = True

    def disable(self, flag: str) -> None:
        """Execute disable."""
        self.flags[flag] = False

    def is_enabled(self, flag: str) -> bool:
        """Execute is enabled."""
        return self.flags.get(flag, False)

    def toggle(self, flag: str) -> None:
        """Execute toggle."""
        self.flags[flag] = not self.flags.get(flag, False)

    def list(self) -> dict:
        """Execute list."""
        return self.flags.copy()


feature_flags = FeatureFlags()
