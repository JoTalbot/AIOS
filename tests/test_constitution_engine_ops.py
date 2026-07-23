"""Constitution engine ops."""
from aios_core.constitution_engine import ConstitutionEngine
def test_ce(): s = ConstitutionEngine().stats(); assert isinstance(s, dict)
