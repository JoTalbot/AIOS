"""Constructor and public-state coverage for ten independent core modules."""
from aios_core.adversarial import AdversarialDefense
from aios_core.bayesian import BayesianInference
from aios_core.blockchain import Blockchain
from aios_core.brain_computer import BCIInterface
from aios_core.category_theory import Category
from aios_core.causal_inference import CausalInference
from aios_core.chaos_testing import ChaosTester
from aios_core.continual_learning import ContinualLearner
from aios_core.creativity import CreativityEngine
from aios_core.differential_privacy import DifferentialPrivacy


def test_adversarial_module_initializes_and_validates_input():
    engine = AdversarialDefense()
    assert engine.validate_input([0.1, 0.2])
    assert "events" in engine.stats()


def test_bayesian_module_initializes_and_tracks_hypothesis():
    engine = BayesianInference()
    engine.add_hypothesis("h", prior=0.6)
    assert engine.get_belief("h") == 0.6


def test_blockchain_genesis_is_valid():
    chain = Blockchain(difficulty=1)
    assert chain.is_valid()


def test_brain_computer_connect_disconnect_and_stats():
    bci = BCIInterface(channels=2)
    assert bci.connect()
    bci.disconnect()
    assert bci.stats()["channels"] == 2


def test_category_adds_objects_and_identity():
    category = Category("test")
    category.add_object("A")
    assert category.get_identity("A") is not None


def test_causal_inference_adds_and_queries_links():
    causal = CausalInference()
    causal.add_causal_link("x", "y")
    assert causal.get_effects("x")


def test_chaos_tester_records_injection():
    chaos = ChaosTester(failure_probability=0)
    assert chaos.inject("latency") is not None


def test_continual_learner_rehearsal_lifecycle():
    learner = ContinualLearner(rehearsal_size=2)
    learner.add_rehearsal({"x": 1}, "task")
    assert learner.get_rehearsal()[0]["data"] == {"x": 1}


def test_creativity_registers_domain_and_generates_idea():
    creativity = CreativityEngine()
    creativity.register_domain("sales", keywords=["price"])
    assert creativity.generate_idea("sales") is not None


def test_differential_privacy_noise_and_budget_stats():
    privacy = DifferentialPrivacy(epsilon=1)
    assert isinstance(privacy.add_noise(5.0), float)
    assert "epsilon" in privacy.stats()
