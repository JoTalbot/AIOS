"""Tests for config, event bus, API gateway, and loader modules."""

from aios_core.config_manager import ConfigManager
from aios_core.event_bus import EventBus
from aios_core.constitution_loader import ConstitutionLoader
from aios_core.constitution_validator import ConstitutionValidator


def test_config_manager_stats():
    cm = ConfigManager()
    s = cm.stats()
    assert isinstance(s, dict)


def test_event_bus_stats():
    eb = EventBus()
    s = eb.stats()
    assert isinstance(s, dict)


def test_constitution_loader_stats():
    cl = ConstitutionLoader()
    s = cl.stats()
    assert isinstance(s, dict)


def test_constitution_validator_stats():
    cv = ConstitutionValidator()
    s = cv.stats()
    assert isinstance(s, dict)
