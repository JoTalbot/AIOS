"""federated_analytics test."""
def test(): from aios_core.federated_analytics import FederatedAnalytics; s = FederatedAnalytics().stats(); assert isinstance(s, dict)
