"""Constitution pipeline."""
from aios_core.constitution_engine import ConstitutionEngine
from aios_core.constitution_validator import ConstitutionValidator
from aios_core.constitution_loader import ConstitutionLoader

def test_constitution_flow():
    ce = ConstitutionEngine()
    cv = ConstitutionValidator()
    cl = ConstitutionLoader()
    assert ce.stats() is not None
    assert cv.stats() is not None
    assert cl.stats() is not None
