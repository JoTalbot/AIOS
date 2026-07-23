"""Integration: ML modules full pipeline."""
from aios_core.model_registry import ModelRegistry
from aios_core.model_serving import ModelServer
from aios_core.learning_engine import LearningEngine
def test_ml_pipeline():
    mr = ModelRegistry()
    ms = ModelServer()
    le = LearningEngine()
    assert mr.stats() is not None
    assert ms.stats() is not None
    assert le.stats() is not None
