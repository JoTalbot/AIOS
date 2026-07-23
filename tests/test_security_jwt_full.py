"""JWT security full ops."""
from aios_core.security_jwt import JWTAuth
def test_create(): j=JWTAuth(secret="test-secret-key-32chars!!"); assert j is not None
