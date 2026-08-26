"""Production pipeline smoke tests."""

from core.runtime.production_pipeline import ProductionPipeline


def test_pipeline_without_coordinator():
    result = ProductionPipeline().execute({"task": "test"})
    assert result.status == "noop"
