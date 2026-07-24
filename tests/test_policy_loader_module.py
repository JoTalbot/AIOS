"""Tests for aios_core/policy_loader.py"""
from __future__ import annotations
import pytest
from aios_core.policy_loader import PolicyLoader


@pytest.fixture()
def loader(tmp_path):
    """Create a minimal policies directory for testing."""
    policies_dir = tmp_path / "policies"
    policies_dir.mkdir()
    (policies_dir / "security.yaml").write_text(
        "name: security\nrules:\n  allow_deploy: true\n  require_approval: true\n"
    )
    return PolicyLoader(policies_dir=str(policies_dir))


class TestPolicyLoader:
    def test_create(self, loader):
        assert loader is not None

    def test_get_policy(self, loader):
        result = loader.get_policy("security")
        assert result is not None

    def test_get_security_policy(self, loader):
        result = loader.get_security_policy()
        assert isinstance(result, (dict, type(None)))

    def test_stats(self, loader):
        s = loader.stats()
        assert isinstance(s, dict)
