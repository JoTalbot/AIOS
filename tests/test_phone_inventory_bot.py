"""Telegram inventory command does not expose screen/message content."""
from __future__ import annotations


class API:
    def __init__(self): self.messages = []
    def send_message(self, *args, **kwargs): self.messages.append((args, kwargs))


def test_inventory_intent(monkeypatch):
    import run_telegram_bot as bot
    import aios_core.phone_inventory as inventory

    class Inventory:
        def __init__(self, root): pass
        def record(self): return {"android": "15", "sdk": 35, "companion_version": "0.1", "apps_available": 6, "apps_calibrated": 3, "calibrations_stale": 0, "wireguard_active": True, "availability_drift": []}

    monkeypatch.setattr(inventory, "PhoneInventory", Inventory)
    api = API()
    assert bot._handle_phone_inventory_intent(api, 1, "инвентарь телефона")
    assert "Инвентарь телефона" in str(api.messages[-1][0][1])
