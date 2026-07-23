"""constitution_validator test."""
def test(): from aios_core.constitution_validator import ConstitutionValidator; s = ConstitutionValidator().stats(); assert isinstance(s, dict)
