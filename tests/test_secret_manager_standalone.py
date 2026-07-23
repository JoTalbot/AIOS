"""secret_manager standalone test."""
from aios_core.secret_manager import SecretManager
def test_init(): s = SecretManager().stats(); assert isinstance(s, dict)
