"""Tests for aios_core/constitution_loader.py"""
from __future__ import annotations
import os
import pytest
from aios_core.constitution_loader import ConstitutionLoader


@pytest.fixture()
def loader(tmp_path):
    """Create a minimal constitution directory for testing."""
    const_dir = tmp_path / "constitution"
    const_dir.mkdir()
    # Create a minimal constitution file
    (const_dir / "ARTICLE-I-IDENTITY.md").write_text("""
# Article I: Identity

## MUST
- System MUST identify itself clearly

## MUST NOT
- System MUST NOT impersonate users

## SHOULD
- System SHOULD log all actions

## MAY
- System MAY cache responses
""")
    return ConstitutionLoader(constitution_dir=str(const_dir))


class TestConstitutionLoader:
    def test_get_rules(self, loader):
        rules = loader.get_rules()
        assert isinstance(rules, list)

    def test_get_must_rules(self, loader):
        rules = loader.get_must_rules()
        assert isinstance(rules, list)

    def test_get_must_not_rules(self, loader):
        rules = loader.get_must_not_rules()
        assert isinstance(rules, list)

    def test_get_may_rules(self, loader):
        rules = loader.get_may_rules()
        assert isinstance(rules, list)

    def test_get_should_rules(self, loader):
        rules = loader.get_should_rules()
        assert isinstance(rules, list)

    def test_search_rules(self, loader):
        results = loader.search_rules("identify")
        assert isinstance(results, list)

    def test_check_action(self, loader):
        result = loader.check_action({"action": "identify", "risk": "low"})
        assert isinstance(result, (bool, dict, list))

    def test_stats(self, loader):
        s = loader.stats()
        assert isinstance(s, dict)
