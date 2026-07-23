"""ML ops full scenario."""
from aios_core.model_registry import ModelRegistry
from aios_core.model_serving import ModelServer
from aios_core.learning_engine import LearningEngine
from aios_core.evolution_manager import EvolutionManager
def test_ml_ops():
    for o in [ModelRegistry(), ModelServer(), LearningEngine(), EvolutionManager()]:
        assert o.stats() is not None
