"""Android driver operations."""
from aios_core.android_driver import DriverCapabilities, UIContext
def test_caps(): dc = DriverCapabilities(); assert dc.package == "ua.slando"
def test_context(): ctx = UIContext("<r/>", "com.test", "Main"); assert ctx.package == "com.test"
