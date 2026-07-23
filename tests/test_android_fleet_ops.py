"""Android fleet pool ops."""
from aios_core.android_fleet import DevicePool, DeviceRecord
def test_record(): r = DeviceRecord("emu1", "avd1"); assert r.serial == "emu1"
def test_pool(): p = DevicePool(); assert p.stats() is not None
