"""Тесты для aios_core/security/trust_manager.py (бэклог 02.08, свежий модуль автокодера).

Покрывает: TrustLevel, SecurityConfig (pydantic v2), TrustManager —
нормализацию уровней/таймаутов, криптографические ограничения.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from aios_core.security.trust_manager import (  # noqa: E402
    SecurityConfig,
    TrustLevel,
    TrustManager,
)


class TestTrustLevel:
    def test_values_contains_all(self):
        values = TrustLevel.values()
        assert TrustLevel.LOW.value in values
        assert TrustLevel.MAXIMUM.value in values
        assert len(values) == len(list(TrustLevel))

    def test_from_value_valid(self):
        assert TrustLevel.from_value(TrustLevel.LOW.value) == TrustLevel.LOW

    def test_from_value_invalid_raises(self):
        with pytest.raises(ValueError):
            TrustLevel.from_value(999)


class TestSecurityConfig:
    def test_defaults_valid(self):
        cfg = SecurityConfig()
        assert cfg.min_timeout <= cfg.default_timeout <= cfg.max_timeout
        assert cfg.trust_levels  # непустой список (валидация 02.08)

    def test_invalid_trust_level_rejected(self):
        with pytest.raises(ValueError):
            SecurityConfig(trust_levels=[1, 2, 999])

    def test_empty_trust_levels_rejected(self):
        # fix 02.08 (ffbe9cb1): пустой список уровней запрещён
        with pytest.raises(ValueError, match="cannot be empty"):
            SecurityConfig(trust_levels=[])

    def test_default_timeout_above_max_rejected(self):
        # Field(le=MAX_TIMEOUT_SECONDS) + root_validator: превышение = ошибка, не кап
        with pytest.raises(ValueError):
            SecurityConfig(default_timeout=10**9)

    def test_root_validator_runs(self):
        # гарантия инцидента 02.08: root_validator не должен падать на импорте/создании
        SecurityConfig()


class TestTrustManager:
    def setup_method(self):
        self.tm = TrustManager(SecurityConfig())

    def test_validate_trust_level_enum_passthrough(self):
        assert self.tm.validate_trust_level(TrustLevel.HIGH) == TrustLevel.HIGH

    def test_validate_trust_level_int(self):
        assert self.tm.validate_trust_level(TrustLevel.MEDIUM.value) == TrustLevel.MEDIUM

    def test_validate_trust_level_invalid(self):
        with pytest.raises(ValueError, match="Invalid trust level"):
            self.tm.validate_trust_level(-1)

    def test_timeout_none_returns_default(self):
        assert self.tm.validate_timeout(None) == self.tm.config.default_timeout

    def test_timeout_below_min_raises(self):
        with pytest.raises(ValueError):
            self.tm.validate_timeout(0)

    def test_timeout_above_max_capped(self):
        assert self.tm.validate_timeout(10**9) == self.tm.config.max_timeout

    def test_timeout_valid_passthrough(self):
        assert self.tm.validate_timeout(120) == 120

    def test_hmac_secure_algorithms(self):
        for algo in ("HS256", "HS384", "HS512", "RS256", "RS384", "RS512"):
            assert self.tm.validate_hmac_algorithm(algo) == algo

    def test_hmac_insecure_rejected(self):
        for algo in ("none", "HS1", "MD5", ""):
            with pytest.raises(ValueError):
                self.tm.validate_hmac_algorithm(algo)

    def test_rsa_key_size_ok(self):
        assert self.tm.validate_rsa_key_size(self.tm.config.min_rsa_key_size) \
            == self.tm.config.min_rsa_key_size

    def test_rsa_key_size_too_small(self):
        with pytest.raises(ValueError, match="at least"):
            self.tm.validate_rsa_key_size(self.tm.config.min_rsa_key_size - 1)

    def test_batch_request_missing_fields_rejected(self):
        assert self.tm.validate_batch_request({}) is False
        assert self.tm.validate_batch_request({"batch_id": "x"}) is False
