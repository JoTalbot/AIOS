"""secret_manager smoke test."""
def test_sm(): from aios_core.secret_manager import SecretManager; assert SecretManager() is not None
