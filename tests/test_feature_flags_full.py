"""Feature flags full."""
from aios_core.feature_flags import FeatureFlags
def test(): s=FeatureFlags().stats(); assert isinstance(s,dict)
