"""JWT security operations tests."""
from aios_core.security_jwt import JWTAuth
def test_jwt_ops():
    j = JWTAuth(secret="test-secret-32chars-minimum!!")
    assert j is not None
