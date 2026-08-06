#!/usr/bin/env python3
"""CLI для универсального Android Device Adapter AIOS.

По умолчанию UI-снимки обезличены: для текста активного экрана нужен
``--include-text`` и ``--confirm``. Все сценарии, меняющие UI, также требуют
``--confirm``; отправка мессенджера требует отдельного второго подтверждения.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

from aios_core.android_audit import PhoneActionAudit
from aios_core.android_gateway import AndroidGateway
from aios_core.android_phone_workflows import (
    EasyWayPhoneAdapter,
    IMePhoneAdapter,
    UklonPhoneAdapter,
    WhatsAppPhoneAdapter,
    adapter_for,
)

ROOT = Path(__file__).resolve().parent


def _confirmed() -> bool:
    return "--confirm" in sys.argv


def _text_after(index: int) -> str:
    return " ".join(value for value in sys.argv[index:] if value != "--confirm" and value != "--include-text").strip()


def _needs_confirm(action: str) -> dict:
    return {"status": "need_confirm", "action": action}


def main() -> int:
    command = sys.argv[1] if len(sys.argv) > 1 else "status"
    gateway = AndroidGateway(ROOT)
    confirmed = _confirmed()
    if command == "register" and len(sys.argv) >= 3:
        result = gateway.register(sys.argv[2], " ".join(sys.argv[3:]) or "Android phone")
    elif command == "connect":
        result = gateway.connect()
    elif command == "status":
        result = gateway.status()
    elif command == "apps":
        result = gateway.apps()
    elif command == "profiles":
        result = gateway.app_profiles()
    elif command == "companion":
        result = gateway.companion_status()
    elif command == "notifications":
        result = gateway.notifications()
    elif command == "accessibility":
        result = gateway.accessibility()
    elif command == "ui-snapshot":
        result = gateway.ui_snapshot(confirm=confirmed, include_text="--include-text" in sys.argv)
    elif command == "clipboard" and len(sys.argv) >= 3:
        result = gateway.set_clipboard(_text_after(2), confirm=confirmed)
    elif command == "paste":
        result = gateway.paste(confirm=confirmed)
    elif command == "tap-ui" and len(sys.argv) >= 3:
        result = gateway.tap_ui(_text_after(2), confirm=confirmed)
    elif command == "capture-status":
        result = gateway.capture_status()
    elif command == "location-status":
        result = gateway.location_status()
    elif command == "location":
        result = gateway.location(confirm=confirmed)
    elif command == "files":
        result = gateway.files(sys.argv[2] if len(sys.argv) > 2 else "/sdcard/Download")
    elif command == "pull" and len(sys.argv) >= 3:
        result = gateway.pull_file(sys.argv[2], confirm=confirmed)
    elif command == "screenshot":
        result = gateway.screenshot()
    elif command == "ui-dump":
        result = gateway.ui_dump()
    elif command == "open" and len(sys.argv) >= 3:
        result = gateway.open_profile(sys.argv[2], confirm=confirmed)
    elif command == "tap" and len(sys.argv) >= 4:
        result = gateway.tap(int(sys.argv[2]), int(sys.argv[3]), confirm=confirmed)
    elif command == "home":
        result = gateway.key("KEYCODE_HOME", confirm=confirmed)
    elif command == "back":
        result = gateway.key("KEYCODE_BACK", confirm=confirmed)
    elif command == "phone-status" and len(sys.argv) >= 3:
        adapter = adapter_for(sys.argv[2], gateway)
        result = adapter.status() if adapter else {"status": "error", "error": "Неизвестное приложение"}
    elif command == "audit":
        result = {"status": "ok", "events": PhoneActionAudit(ROOT).recent(limit=30)}
    elif command == "calibrate" and len(sys.argv) >= 3:
        adapter = adapter_for(sys.argv[2], gateway)
        result = adapter.calibrate(confirm=confirmed) if adapter else {"status": "error", "error": "Неизвестное приложение"}
    elif command == "whatsapp-open-chat" and len(sys.argv) >= 3:
        result = WhatsAppPhoneAdapter(gateway).open_chat(_text_after(2), confirm=confirmed)
    elif command == "whatsapp-read":
        result = WhatsAppPhoneAdapter(gateway).read_visible_chat() if confirmed else _needs_confirm("whatsapp_read_visible_chat")
    elif command == "whatsapp-draft" and len(sys.argv) >= 3:
        result = WhatsAppPhoneAdapter(gateway).prepare_draft(_text_after(2), confirm=confirmed)
    elif command == "whatsapp-send" and len(sys.argv) >= 3:
        result = WhatsAppPhoneAdapter(gateway).send_draft(sys.argv[2], confirm=confirmed)
    elif command == "ime-draft" and len(sys.argv) >= 3:
        result = IMePhoneAdapter(gateway).prepare_draft(_text_after(2), confirm=confirmed)
    elif command == "ime-send" and len(sys.argv) >= 3:
        result = IMePhoneAdapter(gateway).send_draft(sys.argv[2], confirm=confirmed)
    elif command == "uklon-select-suggestion" and len(sys.argv) >= 3:
        result = UklonPhoneAdapter(gateway).select_visible_suggestion(_text_after(2), confirm=confirmed)
    elif command == "uklon-record-vision-capabilities":
        result = UklonPhoneAdapter(gateway).record_vision_capabilities(confirm=confirmed)
    elif command == "uklon-open-driver":
        result = UklonPhoneAdapter(gateway).open_driver(confirm=confirmed)
    elif command == "uklon-stage-route" and "--to" in sys.argv:
        divider = sys.argv.index("--to")
        pickup = " ".join(sys.argv[2:divider]).strip()
        tail = [value for value in sys.argv[divider + 1:] if value != "--confirm"]
        stops: list[str] = []
        final_tokens: list[str] = []
        index = 0
        while index < len(tail):
            if tail[index] in {"--via", "--stop"} and index + 1 < len(tail):
                stops.append(tail[index + 1])
                index += 2
                continue
            final_tokens.append(tail[index])
            index += 1
        destination = " ".join(final_tokens).strip()
        result = UklonPhoneAdapter(gateway).stage_route(pickup, destination, stops=stops, confirm=confirmed)
    elif command == "uklon-enter" and len(sys.argv) >= 4:
        result = UklonPhoneAdapter(gateway).prepare_address_query(sys.argv[2], sys.argv[3], confirm=confirmed)
    elif command == "easyway-stage-route" and len(sys.argv) >= 3:
        result = EasyWayPhoneAdapter(gateway).stage_route(_text_after(2), confirm=confirmed)
    elif command == "easyway-enter" and len(sys.argv) >= 3:
        result = EasyWayPhoneAdapter(gateway).prepare_destination_query(sys.argv[2], confirm=confirmed)
    elif command == "watch":
        interval = 30
        if "--interval" in sys.argv:
            index = sys.argv.index("--interval")
            if index + 1 < len(sys.argv):
                interval = max(10, int(sys.argv[index + 1]))
        while True:
            result = gateway.connect()
            result["health"] = gateway.status()
            print(json.dumps(result, ensure_ascii=False), flush=True)
            time.sleep(interval)
    else:
        result = {
            "status": "error",
            "error": (
                "register|connect|status|apps|profiles|companion|notifications|accessibility|"
                "ui-snapshot|clipboard|paste|tap-ui|capture-status|location-status|location|files|pull|screenshot|ui-dump|"
                "open|tap|home|back|phone-status|audit|calibrate|whatsapp-open-chat|whatsapp-read|"
                "whatsapp-draft|whatsapp-send|ime-draft|ime-send|uklon-open-driver|"
                "uklon-stage-route|uklon-enter|easyway-stage-route|easyway-enter|watch"
            ),
        }
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    return 0 if result.get("status") in (
        "ok", "offline", "unregistered", "need_confirm", "opened", "draft_ready",
        "send_tapped", "route_staged", "query_entered", "calibrated", "cancelled", "not_installed",
    ) else 1


if __name__ == "__main__":
    raise SystemExit(main())
