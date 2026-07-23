"""Federated analytics full."""
from aios_core.federated_analytics import FederatedAnalytics
def test(): s=FederatedAnalytics().stats(); assert isinstance(s,dict)
