import pytest
from aios_core.federated_learning import FederatedLearning, EdgeProfile, NodeStatus

def test_fl_local_differential_privacy():
    fl = FederatedLearning()
    fl.register_node("node1")
    fl.start_round()
    
    # Enable LDP explicitly
    fl.submit_update("node1", 0.90, samples_count=100, apply_ldp=True)
    node = fl.nodes["node1"]
    
    # Value should have noise added (not exactly 0.90)
    assert node.local_accuracy != 0.90
    assert 0.0 <= node.local_accuracy <= 1.0

def test_fl_secure_aggregation():
    fl = FederatedLearning(enable_sec_agg=True)
    fl.register_node("node1")
    fl.register_node("node2")
    
    fl.start_round(fraction=1.0)
    
    fl.submit_update("node1", 0.8, samples_count=100, apply_ldp=False)
    fl.submit_update("node2", 0.9, samples_count=100, apply_ldp=False)
    
    model = fl.aggregate()
    assert model.accuracy == 0.85
    assert len(fl.sec_aggregator.active_masks) == 0  # Masks cleared

def test_fl_async_mode():
    fl = FederatedLearning(async_mode=True)
    fl.register_node("node1")
    
    fl.start_round()
    
    fl.submit_update("node1", 0.9, samples_count=100, apply_ldp=False)
    
    model = fl.get_model()
    assert model.accuracy > 0.0
    assert fl.stats()["async_mode"] is True

def test_fl_client_selection():
    fl = FederatedLearning()
    fl.register_node("weak_node", profile=EdgeProfile(compute_gflops=1.0))
    fl.register_node("strong_node", profile=EdgeProfile(compute_gflops=100.0))
    
    selected = fl.select_clients(strategy="capability_based", fraction=0.5)
    assert len(selected) == 1
    assert selected[0].node_id == "strong_node"
