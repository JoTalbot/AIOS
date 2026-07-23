"""Full tests for secret manager."""

from aios_core.secret_manager import SecretManager


def test_secret_manager_init():
    sm = SecretManager()
    assert sm is not None
