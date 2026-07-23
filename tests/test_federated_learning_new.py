"""federated_learning test."""
def test(): from aios_core.federated_learning import FederatedLearning; s = FederatedLearning().stats(); assert isinstance(s, dict)
