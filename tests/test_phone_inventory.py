"""Safe Android/Companion inventory tests."""
from __future__ import annotations


class Gateway:
    def __init__(self, root): self.root = root
    def status(self): return {"connected": True, "android": "15"}
    def _companion_request(self, path): return {"android": "15", "sdk": 35}
    def app_profiles(self): return {"profiles": [{"id": "whatsapp", "available": True}]}
    def _shell(self, *args, **kwargs): return "versionName=0.1.0\n"


def test_inventory_records_safe_drift(tmp_path):
    from aios_core.phone_inventory import PhoneInventory

    inventory = PhoneInventory(tmp_path, gateway_factory=Gateway, service_probe=lambda _: True)
    first = inventory.record()
    assert first["apps_available"] == 1
    assert first["companion_version"] == "0.1.0"
    assert inventory.path.stat().st_mode & 0o777 == 0o600
