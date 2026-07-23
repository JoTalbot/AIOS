"""Batch tests for remaining AI safety sub-modules (10 classes)."""

from aios_core.ai_safety_causal_interpretability import CausalInterpretability
from aios_core.ai_safety_debate import DebateProtocol
from aios_core.ai_safety_dictionary_learning import DictionaryLearner
from aios_core.ai_safety_formal_verification import FormalVerifier
from aios_core.ai_safety_governance_advanced import AdvancedAIGovernance
from aios_core.ai_safety_honest_ai import HonestAI
from aios_core.ai_safety_interpretability import SafetyInterpretability
from aios_core.ai_safety_interpretability_advanced import AdvancedInterpretability
from aios_core.ai_safety_multi_agent import MultiAgentSafety
from aios_core.ai_safety_recursive_reward import RecursiveRewardModel
from aios_core.ai_safety_red_teaming_advanced import AdvancedRedTeam
from aios_core.ai_safety_scalable_oversight import ScalableOversight
from aios_core.ai_safety_scientist import AISafetyScientist
from aios_core.ai_safety_sparse_autoencoder import SparseAutoencoder
from aios_core.ai_safety_weak_to_strong import WeakToStrongGeneralization


def test_causal_interpretability_stats():
    s = CausalInterpretability().stats()
    assert isinstance(s, dict)


def test_debate_protocol_stats():
    s = DebateProtocol().stats()
    assert isinstance(s, dict)


def test_dictionary_learner_stats():
    s = DictionaryLearner().stats()
    assert isinstance(s, dict)


def test_formal_verifier_stats():
    s = FormalVerifier().stats()
    assert isinstance(s, dict)


def test_advanced_governance_stats():
    s = AdvancedAIGovernance().stats()
    assert isinstance(s, dict)


def test_honest_ai_stats():
    s = HonestAI().stats()
    assert isinstance(s, dict)


def test_safety_interpretability_stats():
    s = SafetyInterpretability().stats()
    assert isinstance(s, dict)


def test_advanced_interpretability_stats():
    s = AdvancedInterpretability().stats()
    assert isinstance(s, dict)


def test_multi_agent_safety_stats():
    s = MultiAgentSafety().stats()
    assert isinstance(s, dict)


def test_recursive_reward_stats():
    s = RecursiveRewardModel().stats()
    assert isinstance(s, dict)


def test_advanced_red_team_stats():
    s = AdvancedRedTeam().stats()
    assert isinstance(s, dict)


def test_scalable_oversight_stats():
    s = ScalableOversight().stats()
    assert isinstance(s, dict)


def test_ai_safety_scientist_stats():
    s = AISafetyScientist().stats()
    assert isinstance(s, dict)


def test_sparse_autoencoder_stats():
    s = SparseAutoencoder().stats()
    assert isinstance(s, dict)


def test_weak_to_strong_stats():
    s = WeakToStrongGeneralization().stats()
    assert isinstance(s, dict)
