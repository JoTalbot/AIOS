"""Tests for Android modules — batch smoke coverage."""

from aios_core.android_driver import DriverCapabilities, UIContext
from aios_core.android_parser import UIAutomatorParser
from aios_core.android_recorder import ScenarioRecorder
from aios_core.android_registry import AndroidAppRegistry
from aios_core.rate_limiter import RateLimiter
from aios_core.plugin_manager import PluginManager


# Android Driver
def test_driver_capabilities():
    dc = DriverCapabilities(package="com.test.app")
    assert dc.package == "com.test.app"


def test_ui_context():
    ctx = UIContext(xml="<node/>", package="com.test.app", current_activity="MainActivity")
    assert ctx.package == "com.test.app"
    assert ctx.xml == "<node/>"


# Android Parser
def test_parser_empty():
    parser = UIAutomatorParser("<root/>")
    assert parser is not None


# Android Recorder
def test_recorder_stats():
    sr = ScenarioRecorder()
    s = sr.stats()
    assert isinstance(s, dict)


# Android Registry
def test_registry_stats():
    reg = AndroidAppRegistry()
    s = reg.stats()
    assert isinstance(s, dict)


# Plugin Manager
def test_plugin_stats():
    pm = PluginManager()
    s = pm.stats()
    assert isinstance(s, dict)


# Rate Limiter edge case
def test_rate_limiter_defaults():
    rl = RateLimiter()
    assert rl.is_allowed("any") is True
