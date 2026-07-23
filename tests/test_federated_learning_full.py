"""Federated learning full."""
from aios_core.federated_learning import FederatedLearning
def test(): s=FederatedLearning().stats(); assert isinstance(s,dict)
