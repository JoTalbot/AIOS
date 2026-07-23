"""Feature Flags standalone test."""
from aios_core.feature_flags import FeatureFlags
def test_init(): assert FeatureFlags() is not None
