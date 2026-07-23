"""Math/theory deep scenario."""
from aios_core.category_theory import CategoryTheory
from aios_core.topological import TopologicalDataAnalysis
from aios_core.uncertainty import UncertaintyQuantifier
from aios_core.type_theory import TypeTheoryChecker
from aios_core.causal_inference import CausalInference
from aios_core.score_based import ScoreBasedModel

def test_math_stack():
    for obj in [CategoryTheory(), TopologicalDataAnalysis(),
                UncertaintyQuantifier(), TypeTheoryChecker(),
                CausalInference(), ScoreBasedModel()]:
        s = obj.stats()
        assert isinstance(s, dict)
