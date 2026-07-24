"""Behavioral coverage for previously untested numerical core modules (batch A)."""

import random

import pytest

from aios_core.score_based import ScoreBasedModel
from aios_core.state_space import StateSpaceModel
from aios_core.topological import PersistenceDiagram, TopologicalAnalyzer
from aios_core.type_theory import TypeSystem
from aios_core.uncertainty import UncertaintyQuantifier
from aios_core.vector_store import VectorStore
from aios_core.world_model import WorldModel


def test_score_based_schedules_training_sampling_and_stats():
    random.seed(1)
    model = ScoreBasedModel(dim=3, sigma_min=0.1, sigma_max=1.0, num_levels=2)
    assert len(model.noise_schedule) == 2
    assert model.train([[1.0, 2.0, 3.0]], epochs=2)["status"] == "trained"
    assert len(model.langevin_sample(2, num_steps=2)) == 2
    assert len(model.ode_sample(1, num_steps=2)[0]) == 3
    assert len(model.sample(1, method="prior")[0]) == 3
    assert model.stats()["samples_generated"] == 3


@pytest.mark.parametrize("method", ["hippo", "random", "uniform"])
def test_state_space_initialization_modes_and_processing(method):
    random.seed(2)
    model = StateSpaceModel(state_dim=3, init_method=method, discretization="bilinear")
    output = model.forward([1.0, 0.5])
    assert len(output) == 2
    assert len(model.compute_kernel(3)) == 3
    assert len(model.conv_forward([1.0, 2.0])) == 2
    model.set_state([1.0, 2.0, 3.0, 4.0])
    assert model.get_state() == [1.0, 2.0, 3.0]
    model.reset_state()
    assert model.get_state() == [0.0, 0.0, 0.0]


def test_topology_handles_empty_cloud_and_describes_shape():
    analyzer = TopologicalAnalyzer(epsilon=1.1)
    assert analyzer.compute_persistence([])["betti_0"] == 0
    cloud = [[0.0, 0.0], [1.0, 0.0], [5.0, 0.0]]
    matrix = analyzer.distance_matrix(cloud)
    assert matrix[0][1] == matrix[1][0] == 1.0
    result = analyzer.compute_persistence(cloud)
    assert result["betti_0"] == 2
    assert analyzer.extract_features(cloud)[0] >= 1
    assert "euler_characteristic" in analyzer.shape_descriptor(cloud)
    assert PersistenceDiagram(1.0, 3.5).persistence == 2.5


def test_type_system_constraints_composition_proofs_and_stats():
    types = TypeSystem()
    types.define_type("positive", int, [lambda value: value > 0])
    types.define_type("text", str)
    assert types.check_type(2, "positive")
    assert not types.check_type(-1, "positive")
    assert types.validate_term("x", "missing")["valid"] is False
    assert types.product_type("pair", "positive", "text")
    assert types.check_type((3, "ok"), "pair")
    types.union_type("scalar", "positive", "text")
    assert types.check_type("ok", "scalar")
    types.register_term("axiom", 1, "positive")
    assert types.prove("result", ["axiom"])["proven"]
    assert types.is_subtype("positive", "positive")
    types.remove_type("text")
    assert types.stats()["proofs"] == 1


def test_uncertainty_estimation_calibration_and_empty_paths():
    quantifier = UncertaintyQuantifier()
    assert quantifier.confidence_interval("unknown") == (0.0, 0.0)
    assert quantifier.calibrate([], "unknown") == 0.0
    quantifier.add_predictions("a", [1.0, 2.0, 3.0, 5.0])
    quantifier.add_predictions("b", [5.0, 6.0])
    estimate = quantifier.estimate("a", prediction=2.5)
    assert estimate.total > 0 and 0 <= estimate.confidence <= 1
    low, high = quantifier.confidence_interval("a", 0.99)
    assert low < high
    assert quantifier.ensemble_disagreement() > 0
    assert quantifier.calibrate([1.0, 2.5, 2.0, 5.0], "a") >= 0
    assert quantifier.stats()["estimates"] == 1


def test_vector_store_search_filter_delete_and_zero_vector():
    store = VectorStore()
    store.add_batch([
        ("one", [1.0, 0.0], {"kind": "a"}),
        ("two", [0.0, 1.0], {"kind": "b"}),
        ("zero", [0.0, 0.0], {"kind": "a"}),
    ])
    assert store.search([0.0, 0.0]) == []
    assert store.search([1.0, 0.0], metadata_filter={"kind": "a"})[0]["id"] == "one"
    assert store.get("two")["metadata"]["kind"] == "b"
    store.delete("two")
    assert store.get("two") is None
    assert store.stats()["vectors"] == 2


def test_world_model_observe_predict_imagine_dream_and_plan():
    random.seed(3)
    model = WorldModel(imagination_horizon=3)
    model.observe({"x": 1.0}, "forward", {"x": 2.0}, reward=4.0)
    assert set(model.predict({"x": 1.0}, "forward")) == {"x"}
    assert model.predict_reward({"x": 1.0}, "forward") > 0
    assert len(model.imagine(2)) == 2
    dream = model.dream_rollout({"x": 1.0}, horizon=2)
    assert dream["horizon"] == 2 and len(dream["trajectory"]) == 2
    assert len(model.plan({"x": 0.0}, horizon=2)) <= 2
    assert model.stats()["observations"] == 1
