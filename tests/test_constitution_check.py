from aios_core.constitution_engine import ConstitutionEngine
def test_check():
    ce = ConstitutionEngine()
    assert ce.stats() is not None