"""feature_flags test."""
def test(): from aios_core.feature_flags import FeatureFlags; s = FeatureFlags().stats(); assert isinstance(s, dict)
