"""security_jwt smoke test."""
def test_jwt(): from aios_core.security_jwt import JWTAuth; assert JWTAuth(secret="test-secret-32chars-min!!").stats() is not None
