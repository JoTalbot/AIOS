"""X-test 3339."""
from aios_core.model_registry import ModelRegistry
from aios_core.model_serving import ModelServer
from aios_core.learning_engine import LearningEngine
from aios_core.evolution_manager import EvolutionManager
from aios_core.automl import AutoML
from aios_core.explainable_ai import ExplainableAI
from aios_core.anomaly_detection import AnomalyDetector
from aios_core.predictive_autonomy import PredictiveAutonomyRegulator

def test():
    for o in [ModelRegistry(),ModelServer(),LearningEngine(),EvolutionManager(),
              AutoML(),ExplainableAI(),AnomalyDetector(),PredictiveAutonomyRegulator()]:
        s = o.stats()
        assert s is not None
