"""Tests for safe query-only route entry; no booking or result selection."""
from __future__ import annotations


class RouteGateway:
    def __init__(self, root, package):
        self.root = root
        self.package = package
        self.active = package
        self.screen = "home"
        self.clipboard = ""
        self.query = ""
        self.taps = []

    def app_profiles(self):
        return {"status": "ok", "profiles": [
            {"id": "uklon", "installed": ["ua.com.uklontaxi"]},
            {"id": "easyway", "installed": ["com.eway"]},
        ]}

    def apps(self, limit=2000):
        return {"status": "ok", "apps": ["ua.com.uklontaxi", "com.eway"]}

    def open_app(self, package, confirm=False):
        self.active = package
        self.package = package
        self.screen = "home"
        return {"status": "ok", "package": package}

    def _nodes(self, include_text=True):
        if self.screen == "query":
            return [{
                "text": self.query if include_text else "", "description": "", "resource": "search",
                "class": "EditText", "clickable": True, "editable": True, "bounds": [20, 120, 550, 190],
            }]
        if self.package == "ua.com.uklontaxi":
            return [
                {"text": "", "description": "", "resource": "buttonPickUpAddress", "class": "View",
                 "clickable": True, "editable": False, "bounds": [20, 300, 550, 370]},
                {"text": "", "description": "", "resource": "buttonDropOffAddress", "class": "View",
                 "clickable": True, "editable": False, "bounds": [20, 380, 550, 450]},
            ]
        return [{
            "text": "Куди", "description": "", "resource": "", "class": "Button",
            "clickable": True, "editable": False, "bounds": [120, 72, 552, 144],
        }]

    def active_app_ui(self, package, confirm=False, include_text=True):
        if package != self.active:
            return {"status": "wrong_active_app", "expected_package": package, "active_package": self.active}
        return {"status": "ok", "package": package, "nodes": self._nodes(include_text)}

    def tap(self, x, y, confirm=False):
        self.taps.append((x, y))
        if self.screen == "home":
            self.screen = "query"
        return {"status": "ok"}

    def set_clipboard(self, text, confirm=False):
        self.clipboard = text
        return {"status": "ok"}

    def paste(self, confirm=False):
        self.query = self.clipboard
        return {"status": "ok"}

    def notifications(self, limit=60):
        return {"status": "ok", "notifications": []}

    def accessibility(self):
        return {"status": "ok", "enabled": True}

    def ui_snapshot(self, confirm=False, include_text=False):
        return {"status": "ok", "package": self.active, "nodes": self._nodes(include_text)}


def test_uklon_query_is_typed_but_never_selects_or_orders(tmp_path):
    from aios_core.android_phone_workflows import UklonPhoneAdapter

    gateway = RouteGateway(tmp_path, "ua.com.uklontaxi")
    adapter = UklonPhoneAdapter(gateway)
    staged = adapter.stage_route("Точка А", "Точка Б", confirm=True)
    assert staged["status"] == "route_staged"
    route_id = staged["route_id"]
    assert adapter.prepare_address_query(route_id, "pickup")["status"] == "need_confirm"
    result = adapter.prepare_address_query(route_id, "pickup", confirm=True)
    assert result["status"] == "query_entered"
    assert gateway.query == "Точка А"
    # Only trigger/input taps happened; there is no route result/order action.
    assert len(gateway.taps) == 2


def test_easyway_query_is_typed_but_route_remains_manual(tmp_path):
    from aios_core.android_phone_workflows import EasyWayPhoneAdapter

    gateway = RouteGateway(tmp_path, "com.eway")
    adapter = EasyWayPhoneAdapter(gateway)
    staged = adapter.stage_route("Центральная остановка", confirm=True)
    assert staged["status"] == "route_staged"
    route_id = staged["route_id"]
    assert adapter.prepare_destination_query(route_id)["status"] == "need_confirm"
    result = adapter.prepare_destination_query(route_id, confirm=True)
    assert result["status"] == "query_entered"
    assert gateway.query == "Центральная остановка"
    assert len(gateway.taps) == 2
