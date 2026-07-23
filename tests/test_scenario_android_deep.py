"""Android stack deep scenario."""
from aios_core.android_driver import DriverCapabilities, UIContext
from aios_core.android_parser import UIElement, UIAutomatorParser
from aios_core.android_registry import AndroidAppRegistry
from aios_core.android_recorder import ScenarioRecorder
from aios_core.android_rpa_bridge import AndroidRPAManager

def test_android_stack():
    assert DriverCapabilities(package="com.test").package == "com.test"
    assert UIContext("<r/>", "pkg", "act").package == "pkg"
    assert UIElement("id","t","c",(0,0,10,10),True,True,"p").text == "t"
    assert AndroidAppRegistry().stats() is not None
    assert AndroidRPAManager().stats() is not None
