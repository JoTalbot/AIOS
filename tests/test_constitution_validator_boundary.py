"""constitution_validator boundary test."""
from aios_core.constitution_validator import ConstitutionValidator

def test(): assert ConstitutionValidator().stats() is not None
