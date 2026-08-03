"""Тесты confirmation-gated сценариев Android-приложений без реального телефона."""
from __future__ import annotations


class FakeGateway:
    def __init__(self, root):
        self.root = root
        self.active = "com.whatsapp"
        self.clipboard = ""
        self.taps = []
        self.sessions = {}
        self.input_text = ""
        self._nodes = [
            {"description": "Поиск", "resource": "", "class": "Button", "clickable": True, "editable": False,
             "bounds": [500, 20, 570, 90], "text": ""},
            {"text": "Иван", "description": "", "resource": "", "class": "TextView", "clickable": False, "editable": False,
             "bounds": [20, 180, 220, 240]},
            {"text": "", "description": "", "resource": "", "class": "FrameLayout", "clickable": True, "editable": False,
             "bounds": [10, 150, 560, 270]},
            {"text": "", "description": "", "resource": "composer", "class": "EditText", "clickable": True, "editable": True,
             "bounds": [20, 1080, 460, 1240]},
            {"text": "", "description": "Отправить", "resource": "send", "class": "ImageButton", "clickable": True, "editable": False,
             "bounds": [480, 1080, 570, 1240]},
        ]

    def app_profiles(self):
        return {"status": "ok", "profiles": [
            {"id": "whatsapp", "installed": ["com.whatsapp"]},
            {"id": "easyway", "installed": ["com.eway"]},
        ]}

    def apps(self, limit=2000):
        return {"status": "ok", "apps": ["com.whatsapp", "com.eway"]}

    def accessibility(self):
        return {"status": "ok", "enabled": True}

    def ui_snapshot(self, confirm=False, include_text=False):
        return {"status": "ok", "package": self.active, "nodes": self._snapshot_nodes(include_text)}

    def active_app_ui(self, package, confirm=False, include_text=False):
        if self.active != package:
            return {"status": "wrong_active_app", "expected_package": package, "active_package": self.active}
        return {"status": "ok", "package": self.active, "nodes": self._snapshot_nodes(include_text)}

    def _snapshot_nodes(self, include_text):
        items = []
        for source in self._nodes:
            item = dict(source)
            if source.get("editable"):
                item["text"] = self.input_text
            if not include_text:
                item.pop("text", None)
                item.pop("description", None)
            items.append(item)
        return items

    def open_app(self, package, confirm=False):
        self.active = package
        return {"status": "ok", "package": package}

    def tap(self, x, y, confirm=False):
        self.taps.append((x, y, confirm))
        return {"status": "ok"}

    def set_clipboard(self, text, confirm=False):
        self.clipboard = text
        return {"status": "ok", "length": len(text)}

    def paste(self, confirm=False):
        self.input_text = self.clipboard
        return {"status": "ok"}

    def begin_control_session(self, package, purpose, ttl_seconds=300):
        self.sessions["lease"] = package
        return {"status": "ok", "session_id": "lease"}

    def validate_control_session(self, session_id, package):
        return {"status": "ok"} if self.sessions.get(session_id) == package else {"status": "expired"}

    def end_control_session(self, session_id):
        self.sessions.pop(session_id, None)

    def notifications(self, limit=60):
        return {"status": "ok", "notifications": []}


def test_whatsapp_chat_and_draft_are_two_confirmation_steps(tmp_path):
    from aios_core.android_phone_workflows import WhatsAppPhoneAdapter

    gateway = FakeGateway(tmp_path)
    adapter = WhatsAppPhoneAdapter(gateway)
    assert adapter.open_chat("Иван")["status"] == "need_confirm"
    assert adapter.open_chat("Иван", confirm=True)["status"] == "opened"

    assert adapter.prepare_draft("Привет")["status"] == "need_confirm"
    draft = adapter.prepare_draft("Привет", confirm=True)
    assert draft["status"] == "draft_ready"
    assert adapter.send_draft(draft["draft_id"])["status"] == "need_confirm"
    assert adapter.send_draft(draft["draft_id"], confirm=True)["status"] == "send_tapped"
    assert gateway.sessions == {}


def test_whatsapp_blocks_send_if_phone_text_changed(tmp_path):
    from aios_core.android_phone_workflows import WhatsAppPhoneAdapter

    gateway = FakeGateway(tmp_path)
    adapter = WhatsAppPhoneAdapter(gateway)
    draft = adapter.prepare_draft("Проверочный текст", confirm=True)
    assert draft["status"] == "draft_ready"
    # Even a capitalization-only manual edit must stop sending; whitespace/
    # case-insensitive comparison would be unsafe here.
    gateway.input_text = "проверочный текст"
    result = adapter.send_draft(draft["draft_id"], confirm=True)
    assert result["status"] == "draft_changed"
    assert not any(x[:2] == (525, 1160) for x in gateway.taps[-1:])


def test_visible_messages_mask_codes_and_cards(tmp_path):
    from aios_core.android_phone_workflows import WhatsAppPhoneAdapter

    gateway = FakeGateway(tmp_path)
    gateway._nodes.append({
        "text": "Код 123456, карта 4444 3333 2222 1111", "description": "", "resource": "",
        "class": "TextView", "clickable": False, "editable": False, "bounds": [10, 300, 500, 360],
    })
    values = WhatsAppPhoneAdapter(gateway).read_visible_chat()["messages"]
    joined = " ".join(values)
    assert "123456" not in joined
    assert "4444" not in joined
    assert "[код скрыт]" in joined


def test_route_selectors_are_specific_to_calibrated_controls(tmp_path):
    from aios_core.android_phone_workflows import EasyWayPhoneAdapter, UklonPhoneAdapter

    gateway = FakeGateway(tmp_path)
    uklon = UklonPhoneAdapter(gateway)
    assert uklon._calibration_selectors([
        {"resource": "buttonPickUpAddress", "clickable": True, "bounds": [10, 100, 500, 160]},
        {"resource": "buttonDropOffAddress", "clickable": True, "bounds": [10, 170, 500, 230]},
    ]) == {"pickup_address": True, "destination_address": True}

    easyway = EasyWayPhoneAdapter(gateway)
    assert easyway._calibration_selectors([
        {"text": "Куди", "description": "", "resource": "", "class": "Button", "clickable": True,
         "bounds": [120, 72, 552, 144]},
    ]) == {"destination_trigger": True}


def test_easyway_uses_the_installed_com_eway_profile(tmp_path):
    from aios_core.android_phone_workflows import EasyWayPhoneAdapter

    status = EasyWayPhoneAdapter(FakeGateway(tmp_path)).status()
    assert status["available"] is True
    assert status["package"] == "com.eway"
