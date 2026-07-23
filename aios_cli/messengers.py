#!/usr/bin/env python3
"""AIOS CLI — WhatsApp, Viber, Facebook messenger commands."""

import argparse
import json
import os
from pathlib import Path
def _lazy_import(module_path: str, attr: str = None):
    """Import module on first use and cache result."""
    key = (module_path, attr)
    if key not in _import_cache:
        import importlib
        mod = importlib.import_module(module_path)
        _import_cache[key] = getattr(mod, attr) if attr else mod
    return _import_cache[key]

DEFAULT_OLX_DB = "olx_ads.sqlite"


def _run_msg_platform(args, platform: str) -> bool:
    """Generic guarded-messenger CLI для платформ HintsMessenger."""
    cmd = getattr(args, "messenger_command", None) or "doctor"
    camel = {
        "whatsapp": "WhatsApp",
        "viber": "Viber",
        "tiktok": "TikTok",
        "facebook": "Facebook",
    }.get(platform, platform.capitalize())
    try:
        module = __import__(
            f"aios_core.modules.{platform}",
            fromlist=[f"{camel}Bootstrap", f"{camel}Messenger", f"{camel}Storage"],
        )
        bootstrap_cls = getattr(module, f"{camel}Bootstrap")
        messenger_cls = getattr(module, f"{camel}Messenger")
        storage_cls = getattr(module, f"{camel}Storage")
        if cmd == "doctor":
            report = bootstrap_cls(
                serial=getattr(args, "serial", None),
            ).doctor()
            print(json.dumps(report, ensure_ascii=False, indent=2))
            return True
        if cmd == "dm-send":
            # compliance-контур ДО сборки adb/storage: запрещённое
            # действие не должно даже инициализировать устройство.
            from aios_core.platforms.compliance import compliance_guard

            check = compliance_guard(
                platform,
                "auto_send" if args.auto_send else "send",
                directory=getattr(args, "directory", "platforms"),
            )
            if not check["allowed"]:
                print(
                    json.dumps(
                        {"error": check["reason"], "compliance": check},
                        ensure_ascii=False,
                        indent=2,
                    )
                )
                return True
        from aios_core.modules.olx.adb import ADBController

        package = messenger_cls.PACKAGE
        adb = ADBController(package=package, serial=getattr(args, "serial", None))
        messenger = messenger_cls(
            adb=adb,
            storage=storage_cls(getattr(args, "db", f"data/{platform}.sqlite")),
            directory=getattr(args, "directory", "platforms"),
        )
        if cmd == "chats":
            messenger.open_chats()
            threads = messenger.list_chats()
            print(json.dumps([t.to_dict() for t in threads], ensure_ascii=False, indent=2))
            return True
        if cmd == "dm-send":
            result = messenger.send_reply(
                args.chat, args.text, interlocutor=getattr(args, "interlocutor", None), auto_send=args.auto_send
            )
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return True
        if cmd == "dm-flush":
            results = messenger.flush_outbox()
            print(json.dumps({"flushed": results}, ensure_ascii=False, indent=2))
            return True
        if cmd == "dm-outbox":
            storage = storage_cls(getattr(args, "db", f"data/{platform}.sqlite"))
            try:
                rows = storage.outbox_list(status=getattr(args, "status", None))
            finally:
                storage.close()
            print(json.dumps(rows, ensure_ascii=False, indent=2))
            return True
    except ValueError as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False))
        return True
    return False

