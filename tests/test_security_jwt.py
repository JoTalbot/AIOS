"""Security regression tests for JWT credential handling."""

import pytest

from aios_core.security_jwt import JWTManager


def test_jwt_manager_requires_strong_secret(monkeypatch):
    monkeypatch.delenv("AIOS_JWT_SECRET", raising=False)
    with pytest.raises(ValueError, match="JWT secret must be supplied"):
        JWTManager()
    with pytest.raises(ValueError, match="at least 32"):
        JWTManager("too-short")


def test_jwt_manager_uses_explicit_strong_secret_and_revokes_token():
    manager = JWTManager("a" * 32)
    token = manager.create_token("operator", roles=["admin"], scopes=["admin:write"])
    assert manager.check_role(token, "admin")
    assert manager.check_scope(token, "admin:write")
    assert manager.revoke_token(token)
    assert manager.verify_token(token) is None


def test_jwt_manager_reads_secret_from_environment(monkeypatch):
    monkeypatch.setenv("AIOS_JWT_SECRET", "b" * 32)
    token = JWTManager().create_token("service")
    assert JWTManager().verify_token(token)["sub"] == "service"
