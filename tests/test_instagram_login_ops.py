"""Instagram login tests."""
from aios_core.modules.instagram.login import LoginDriver
def test_login_exists():
    assert LoginDriver is not None
