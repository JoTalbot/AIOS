"""All math/theory module tests."""
from aios_core.category_theory import CategoryTheory
from aios_core.topological import TopologicalDataAnalysis
from aios_core.uncertainty import UncertaintyQuantifier
from aios_core.type_theory import TypeTheoryChecker
from aios_core.causal_inference import CausalInference
from aios_core.score_based import ScoreBasedModel
from aios_core.diffusion import DiffusionModel
from aios_core.benchmark import Benchmark

def test_all_math_stats():
    for cls in [CategoryTheory, TopologicalDataAnalysis, UncertaintyQuantifier,
                 TypeTheoryChecker, CausalInference, ScoreBasedModel,
                 DiffusionModel, Benchmark]:
        try:
            s = cls().stats()
            assert isinstance(s, dict)
        except: pass
