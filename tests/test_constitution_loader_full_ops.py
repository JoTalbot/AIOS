"""Constitution loader full ops."""
from aios_core.constitution_loader import ConstitutionLoader
def test_cl(): assert ConstitutionLoader().stats() is not None
