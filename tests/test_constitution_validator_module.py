"""Tests for aios_core/constitution_validator.py"""
from __future__ import annotations
import pytest
from aios_core.constitution_validator import ConstitutionValidator


@pytest.fixture()
def validator(tmp_path):
    const_dir = tmp_path / "constitution"
    const_dir.mkdir()
    policies_dir = tmp_path / "policies"
    policies_dir.mkdir()
    (const_dir / "ARTICLE-I-IDENTITY.md").write_text("""
# Article I: Identity

## MUST
- System MUST identify itself clearly

## MUST NOT
- System MUST NOT impersonate users
""")
    (policies_dir / "security.yaml").write_text(
        "name: security\nrules:\n  allow_deploy: true\n"
    )
    return ConstitutionValidator(constitution_dir=str(const_dir), policies_dir=str(policies_dir))


class TestConstitutionValidator:
    def test_create(self, validator):
        assert validator is not None

    def test_validate(self, validator):
        result = validator.validate(action={"action": "identify", "risk": "low"})
        assert isinstance(result, (bool, dict, list))

    def test_report(self, validator):
        result = validator.report()
        assert isinstance(result, dict)
