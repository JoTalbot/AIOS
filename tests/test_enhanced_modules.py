"""Tests for Enhanced modules — logging, monitoring, protocols."""

from aios_core.enhanced_logging import EnhancedLogger
from aios_core.enhanced_monitoring import MonitoringAPI
from aios_core.enhanced_protocols import ProtocolManager


def test_enhanced_logger_stats():
    el = EnhancedLogger()
    s = el.stats()
    assert isinstance(s, dict)


def test_monitoring_api_stats():
    ma = MonitoringAPI()
    s = ma.stats()
    assert isinstance(s, dict)


def test_protocol_manager_stats():
    pm = ProtocolManager()
    s = pm.stats()
    assert isinstance(s, dict)
