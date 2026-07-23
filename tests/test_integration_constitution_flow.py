"""Integration test — constitution pipeline."""
from aios_core.constitution_engine import ConstitutionEngine
from aios_core.constitution_validator import ConstitutionValidator
def test_pipeline_objects():
    assert ConstitutionEngine() is not None
    assert ConstitutionValidator() is not None
