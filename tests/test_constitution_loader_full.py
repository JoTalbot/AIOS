"""Constitution loader full tests."""
from aios_core.constitution_loader import ConstitutionLoader
def test_loader(): assert ConstitutionLoader().stats() is not None
