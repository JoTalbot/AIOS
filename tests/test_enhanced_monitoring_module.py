"""Tests for aios_core/enhanced_monitoring.py"""
from __future__ import annotations
import pytest
from aios_core.enhanced_monitoring import MonitoringAPI


class TestMonitoringAPI:
    def test_create(self):
        api = MonitoringAPI()
        assert api is not None
