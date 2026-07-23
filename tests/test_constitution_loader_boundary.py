"""constitution_loader boundary test."""
from aios_core.constitution_loader import ConstitutionLoader

def test(): assert ConstitutionLoader().stats() is not None
