"""Integration: Android modules stack."""
from aios_core.android_driver import DriverCapabilities, UIContext
from aios_core.android_registry import AndroidAppRegistry
from aios_core.android_parser import UIElement

def test_android_stack():
    dc = DriverCapabilities(package="com.test.app")
    ctx = UIContext("<root/>", "com.test.app", "MainActivity")
    ar = AndroidAppRegistry()
    el = UIElement("rid", "text", "cls", (0,0,100,100), True, True, "pkg")
    assert dc.package == "com.test.app"
    assert ctx.package == "com.test.app"
    assert ar.stats() is not None
    assert el.text == "text"
