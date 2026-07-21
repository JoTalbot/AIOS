"""Feature Flags for AIOS"""

from typing import Dict


class FeatureFlags:
    """Simple feature flag system."""

    def __init__(self):
        self.flags: Dict[str, bool] = {}

    def enable(self, flag: str):
        self.flags[flag] = True

    def disable(self, flag: str):
        self.flags[flag] = False

    def is_enabled(self, flag: str) -> bool:
        return self.flags.get(flag, False)

    def toggle(self, flag: str):
        self.flags[flag] = not self.flags.get(flag, False)

    def list(self) -> dict:
        return self.flags.copy()


feature_flags = FeatureFlags()