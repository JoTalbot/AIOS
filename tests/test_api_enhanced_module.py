"""Tests for aios_core/api/enhanced.py"""
from __future__ import annotations
import pytest
from aios_core.api.enhanced import EnhancedAIOSAPI


@pytest.fixture()
def api(tmp_path):
    return EnhancedAIOSAPI(db_path=str(tmp_path / "test.db"))


class TestEnhancedAIOSAPI:
    def test_create(self, api):
        assert api is not None
