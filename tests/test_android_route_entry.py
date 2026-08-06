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


def test_query_dismisses_recognised_keyboard_before_verification(tmp_path):
    from aios_core.android_phone_workflows import UklonPhoneAdapter

    class KeyboardGateway:
        def __init__(self, root):
            self.root = root
            self.ime = False
            self.clipboard = ""
            self.value = ""
            self.key_events = []
        def active_app_ui(self, package, confirm=False, include_text=True):
            if self.ime:
                return {"status": "wrong_active_app", "expected_package": package, "active_package": "com.google.android.inputmethod.latin"}
            return {"status": "ok", "package": package, "nodes": [{"text": self.value, "editable": True, "clickable": True, "bounds": [1, 1, 100, 50]}]}
        def tap(self, x, y, confirm=False): return {"status": "ok"}
        def set_clipboard(self, text, confirm=False): self.clipboard = text; return {"status": "ok"}
        def paste(self, confirm=False): self.value = self.clipboard; self.ime = True; return {"status": "ok"}
        def key(self, keycode, confirm=False): self.key_events.append(keycode); self.ime = False; return {"status": "ok"}

    gateway = KeyboardGateway(tmp_path)
    result = UklonPhoneAdapter(gateway)._enter_visible_query("Точка", wait_seconds=1)
    assert result["status"] == "query_entered"
    assert gateway.key_events == ["KEYCODE_BACK"]

    gateway.ime = True
    gateway.key_events = []
    result = UklonPhoneAdapter(gateway)._enter_visible_query("Ещё точка", wait_seconds=1)
    assert result["status"] == "query_entered"
    assert gateway.key_events == ["KEYCODE_BACK", "KEYCODE_BACK"]


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


def test_uklon_route_supports_ordered_intermediate_stops(tmp_path):
    from aios_core.android_phone_workflows import UklonPhoneAdapter

    gateway = RouteGateway(tmp_path, "ua.com.uklontaxi")
    adapter = UklonPhoneAdapter(gateway)
    staged = adapter.stage_route("Точка А", "Точка В", stops=["Точка Б"], confirm=True)
    assert staged["status"] == "route_staged"
    assert staged["destination_count"] == 2
    assert staged["stop_count"] == 1

    route = adapter.store.get(staged["route_id"], kind="route_draft", package="ua.com.uklontaxi")
    assert route["data"]["route_points"] == ["Точка Б", "Точка В"]
    assert route["data"]["stops"] == [{"order": 1, "address": "Точка Б"}]
    assert adapter.prepare_address_query(staged["route_id"], "stop_1")["status"] == "need_confirm"
    entered = adapter.prepare_address_query(staged["route_id"], "via:1", confirm=True)
    assert entered["status"] == "query_entered"
    assert entered["field"] == "stop_1"
    assert gateway.query == "Точка Б"


def test_uklon_route_accepts_compact_ordered_destination_sequence(tmp_path):
    from aios_core.android_phone_workflows import UklonPhoneAdapter

    gateway = RouteGateway(tmp_path, "ua.com.uklontaxi")
    staged = UklonPhoneAdapter(gateway).stage_route("Точка А", ["Точка Б", "Точка В"], confirm=True)
    assert staged["status"] == "route_staged"
    route = UklonPhoneAdapter(gateway).store.get(staged["route_id"], kind="route_draft", package="ua.com.uklontaxi")
    assert route["data"]["stops"] == [{"order": 1, "address": "Точка Б"}]
    assert route["data"]["final_destination"] == "Точка В"


def test_uklon_route_limits_destination_count(tmp_path):
    from aios_core.android_phone_workflows import UklonPhoneAdapter

    gateway = RouteGateway(tmp_path, "ua.com.uklontaxi")
    adapter = UklonPhoneAdapter(gateway)
    result = adapter.stage_route("Точка А", "Финал", stops=[str(i) for i in range(adapter.MAX_ROUTE_DESTINATIONS)], confirm=True)
    assert result["status"] == "error"
    assert "максимум" in result["error"]


def test_uklon_status_exposes_verified_route_capabilities(tmp_path):
    import json

    from aios_core.android_phone_workflows import UklonPhoneAdapter

    data = tmp_path / "data" / "android_gateway"
    data.mkdir(parents=True)
    (data / "app_ui_calibrations.json").write_text(json.dumps({
        "uklon": {
            "package": "ua.com.uklontaxi",
            "selectors": {"pickup_address": True, "destination_address": True},
            "capabilities": {
                "alternate_pickup": True,
                "multi_stop_add": True,
                "multi_stop_delete": True,
                "multi_stop_reorder": True,
                "booking_automation": False,
                "evidence": "manual_vision_review",
                "verified_at": "2026-08-06T00:00:00+00:00",
            },
        },
    }), encoding="utf-8")
    status = UklonPhoneAdapter(RouteGateway(tmp_path, "ua.com.uklontaxi")).status()
    assert status["route_capabilities"]["multi_stop_reorder"] is True
    assert status["route_capabilities"]["booking_automation"] is False
    assert "evidence" not in status["route_capabilities"]


def test_uklon_selects_only_one_visible_suggestion(tmp_path):
    from aios_core.android_phone_workflows import UklonPhoneAdapter

    gateway = RouteGateway(tmp_path, "ua.com.uklontaxi")
    gateway._suggestion_nodes = [{
        "text": "Точка Б", "description": "", "resource": "", "class": "TextView",
        "clickable": True, "editable": False, "bounds": [20, 100, 550, 180],
    }]
    gateway._nodes = lambda include_text=True: gateway._suggestion_nodes
    adapter = UklonPhoneAdapter(gateway)
    assert adapter.select_visible_suggestion("Точка Б")["status"] == "need_confirm"
    result = adapter.select_visible_suggestion("Точка Б", confirm=True)
    assert result == {"status": "suggestion_selected", "booking": "not_created"}
    assert gateway.taps == [(285, 140)]


def test_uklon_refuses_ambiguous_visible_suggestions(tmp_path):
    from aios_core.android_phone_workflows import UklonPhoneAdapter

    gateway = RouteGateway(tmp_path, "ua.com.uklontaxi")
    gateway._suggestion_nodes = [
        {"text": "Парк, 1", "description": "", "resource": "", "class": "TextView",
         "clickable": True, "editable": False, "bounds": [20, 100, 550, 180]},
        {"text": "Парк, 2", "description": "", "resource": "", "class": "TextView",
         "clickable": True, "editable": False, "bounds": [20, 190, 550, 270]},
    ]
    gateway._nodes = lambda include_text=True: gateway._suggestion_nodes
    result = UklonPhoneAdapter(gateway).select_visible_suggestion("Парк", confirm=True)
    assert result["status"] == "error"
    assert "несколько" in result["error"]
    assert gateway.taps == []
