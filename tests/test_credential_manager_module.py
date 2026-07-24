"""Tests for aios_core/credential_manager.py"""
from __future__ import annotations
import pytest
from aios_core.credential_manager import CredentialManager, CredentialEntry, CredentialType


@pytest.fixture()
def manager():
    return CredentialManager(passphrase="test-passphrase-123")


class TestCredentialEntry:
    def test_create(self):
        e = CredentialEntry(credential_id="c1", platform="olx", credential_type=CredentialType.API_KEY)
        assert e.credential_id == "c1"

    def test_age_days_is_property(self):
        e = CredentialEntry(credential_id="c1", platform="olx", credential_type=CredentialType.API_KEY)
        assert isinstance(e.age_days, (int, float))

    def test_needs_rotation(self):
        e = CredentialEntry(credential_id="c1", platform="olx", credential_type=CredentialType.PASSWORD)
        assert isinstance(e.needs_rotation, bool)


class TestCredentialManager:
    def test_store(self, manager):
        entry = manager.store(platform="olx", credential_type=CredentialType.API_KEY, value="sk-12345")
        assert isinstance(entry, CredentialEntry)
        assert entry.platform == "olx"

    def test_retrieve(self, manager):
        entry = manager.store(platform="olx", credential_type=CredentialType.API_KEY, value="val1")
        result = manager.retrieve(entry.credential_id)
        assert result is not None

    def test_retrieve_nonexistent(self, manager):
        assert manager.retrieve("nope") is None

    def test_rotate(self, manager):
        entry = manager.store(platform="olx", credential_type=CredentialType.API_KEY, value="old")
        result = manager.rotate(entry.credential_id, new_value="new")
        assert result is not None

    def test_compromise(self, manager):
        entry = manager.store(platform="olx", credential_type=CredentialType.API_KEY, value="val")
        result = manager.compromise(entry.credential_id, new_value="replaced")
        assert result is not None

    def test_deactivate(self, manager):
        entry = manager.store(platform="olx", credential_type=CredentialType.API_KEY, value="val")
        result = manager.deactivate(entry.credential_id)
        assert result is not None

    def test_activate(self, manager):
        entry = manager.store(platform="olx", credential_type=CredentialType.API_KEY, value="val")
        manager.deactivate(entry.credential_id)
        result = manager.activate(entry.credential_id)
        assert result is not None

    def test_list_credentials(self, manager):
        manager.store(platform="olx", credential_type=CredentialType.API_KEY, value="v1")
        manager.store(platform="instagram", credential_type=CredentialType.TOKEN, value="v2")
        creds = manager.list_credentials()
        assert len(creds) >= 2

    def test_check_rotations(self, manager):
        result = manager.check_rotations()
        assert isinstance(result, list)

    def test_stats(self, manager):
        s = manager.stats()
        assert isinstance(s, dict)
