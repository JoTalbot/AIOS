"""Android registry ops."""
from aios_core.android_registry import AndroidAppRegistry, AndroidAppDescriptor
def test_desc(): d = AndroidAppDescriptor("test", "com.test"); assert d.package == "com.test"
