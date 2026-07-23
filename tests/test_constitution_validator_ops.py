"""Constitution validator ops."""
from aios_core.constitution_validator import ConstitutionValidator
def test_cv(): s = ConstitutionValidator().stats(); assert isinstance(s, dict)
