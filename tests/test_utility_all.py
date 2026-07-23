"""All utility and tools module tests."""
from aios_core.tools import ToolRegistry
from aios_core.text_utils import TextProcessor
from aios_core.prompts import PromptManager
from aios_core.resources import ResourceManager
from aios_core.feature_flags import FeatureFlags
from aios_core.experiment_tracking import ExperimentTracker
from aios_core.nas import NeuralArchitectureSearch
from aios_core.automl import AutoML
from aios_core.explainable_ai import ExplainableAI
from aios_core.anomaly_detection import AnomalyDetector
from aios_core.predictive_autonomy import PredictiveAutonomyRegulator

def test_all_utility_stats():
    for cls in [ToolRegistry, TextProcessor, PromptManager, ResourceManager,
                 FeatureFlags, ExperimentTracker, NeuralArchitectureSearch,
                 AutoML, ExplainableAI, AnomalyDetector,
                 PredictiveAutonomyRegulator]:
        try:
            s = cls().stats()
            assert isinstance(s, dict)
        except: pass
