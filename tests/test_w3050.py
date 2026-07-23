"""W-test 3050."""
from aios_core.model_registry import ModelRegistry
from aios_core.model_serving import ModelServer
from aios_core.learning_engine import LearningEngine
from aios_core.evolution_manager import EvolutionManager
from aios_core.automl import AutoML
from aios_core.explainable_ai import ExplainableAI

def test():
    for o in [ModelRegistry(),ModelServer(),LearningEngine(),EvolutionManager(),AutoML(),ExplainableAI()]:
        s = o.stats()
        assert s is not None
