#!/usr/bin/env python3
"""CLI Phone Brain — управление демоном и очередью задач Android-шлюза.

    run                     запустить демон (foreground, для systemd)
    enqueue KIND [JSON]     поставить задачу [--priority N] [--confirm] [--dedup KEY]
    list [--status S] [-n]  последние задачи
    show ID                 детали задачи
    cancel ID               отменить задачу в очереди
    confirm ID              подтвердить черновик (need_confirm → в работу)
    status                  health демона (API; офлайн — из файлов состояния)
    kinds                   типы задач и их гейты
    metrics                 метрики очереди и счётчики демона
    events [-n]             последние события журнала
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent


def _config_api_port() -> int:
    try:
        cfg = json.loads((ROOT / "data" / "android_gateway" / "phone_brain_config.json").read_text("utf-8"))
        return int(cfg.get("api", {}).get("port") or 8790)
    except Exception:
        return 8790


def _api(method: str, path: str, body: dict | None = None, timeout: float = 4.0) -> dict:
    url = f"http://127.0.0.1:{_config_api_port()}{path}"
    data = json.dumps(body).encode("utf-8") if body is not None else None
    request = urllib.request.Request(url, data=data, method=method,
                                     headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def _store():
    from aios_core.phone_brain.queue_store import JobStore
    return JobStore(ROOT / "data" / "android_gateway" / "phone_brain.db")


def _print(payload: Any) -> int:
    print(json.dumps(payload, ensure_ascii=False, indent=2, default=str))
    return 0 if (not isinstance(payload, dict) or payload.get("status") not in ("error", "failed")) else 1


def cmd_run(args: argparse.Namespace) -> int:
    from aios_core.phone_brain.daemon import PhoneBrainDaemon
    return PhoneBrainDaemon(ROOT).run()


def cmd_enqueue(args: argparse.Namespace) -> int:
    payload: dict = {}
    if args.payload:
        try:
            parsed = json.loads(args.payload)
        except json.JSONDecodeError:
            return _print({"status": "error", "error": "payload должен быть JSON-объектом"})
        if not isinstance(parsed, dict):
            return _print({"status": "error", "error": "payload должен быть JSON-объектом"})
        payload = parsed
    if args.confirm:
        payload["confirm"] = True
    body: dict[str, Any] = {"kind": args.kind, "payload": payload,
                            "priority": args.priority, "dedup_key": args.dedup}
    try:
        return _print(_api("POST", "/jobs", body))
    except (urllib.error.URLError, OSError):
        job = _store().enqueue(args.kind, payload, priority=args.priority, dedup_key=args.dedup)
        job["via"] = "store-direct (API недоступен)"
        return _print(job)


def cmd_list(args: argparse.Namespace) -> int:
    try:
        return _print(_api("GET", f"/jobs?limit={args.limit}"
                                   + (f"&status={args.status}" if args.status else "")))
    except (urllib.error.URLError, OSError):
        return _print({"status": "ok", "jobs": _store().list(status=args.status, limit=args.limit),
                       "via": "store-direct (API недоступен)"})


def cmd_show(args: argparse.Namespace) -> int:
    try:
        return _print(_api("GET", f"/jobs/{args.id}"))
    except (urllib.error.URLError, OSError):
        job = _store().get(args.id)
        return _print({"status": "ok", "job": job} if job else {"status": "error", "error": "job not found"})


def cmd_cancel(args: argparse.Namespace) -> int:
    try:
        return _print(_api("POST", f"/jobs/{args.id}/cancel", {}))
    except (urllib.error.URLError, OSError):
        return _print(_store().cancel(args.id))


def cmd_confirm(args: argparse.Namespace) -> int:
    try:
        return _print(_api("POST", f"/jobs/{args.id}/confirm", {}))
    except (urllib.error.URLError, OSError):
        return _print(_store().confirm_job(args.id))


def cmd_status(args: argparse.Namespace) -> int:
    try:
        return _print(_api("GET", "/health"))
    except (urllib.error.URLError, OSError):
        from aios_core.phone_brain.common import read_json
        data_dir = ROOT / "data" / "android_gateway"
        return _print({"status": "ok", "daemon": "offline (API недоступен)",
                       "device": read_json(data_dir / "health.json", {}),
                       "supervisor": read_json(data_dir / "brain_supervisor.json", {}),
                       "queue": _store().counts()})


def cmd_kinds(args: argparse.Namespace) -> int:
    try:
        return _print(_api("GET", "/kinds"))
    except (urllib.error.URLError, OSError):
        from aios_core.phone_brain.handlers import BUILTIN_HANDLERS
        return _print({"status": "ok", "kinds": [handler.meta() for handler in BUILTIN_HANDLERS],
                       "via": "static (API недоступен)"})


def cmd_metrics(args: argparse.Namespace) -> int:
    try:
        return _print(_api("GET", "/metrics"))
    except (urllib.error.URLError, OSError):
        return _print(_store().metrics())


def cmd_events(args: argparse.Namespace) -> int:
    try:
        return _print(_api("GET", f"/events?limit={args.limit}"))
    except (urllib.error.URLError, OSError):
        from aios_core.phone_brain.events import EventLog
        return _print({"status": "ok",
                       "events": EventLog(ROOT / "data" / "android_gateway" / "phone_brain_events.jsonl")
                       .recent(args.limit), "via": "file-direct (API недоступен)"})


def main() -> int:
    parser = argparse.ArgumentParser(description="AIOS Phone Brain CLI")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("run", help="запустить демон").set_defaults(func=cmd_run)

    enqueue = sub.add_parser("enqueue", help="поставить задачу в очередь")
    enqueue.add_argument("kind")
    enqueue.add_argument("payload", nargs="?", default="")
    enqueue.add_argument("--priority", type=int, default=50)
    enqueue.add_argument("--confirm", action="store_true")
    enqueue.add_argument("--dedup", default=None)
    enqueue.set_defaults(func=cmd_enqueue)

    list_cmd = sub.add_parser("list", help="последние задачи")
    list_cmd.add_argument("--status", default=None)
    list_cmd.add_argument("-n", "--limit", type=int, default=20)
    list_cmd.set_defaults(func=cmd_list)

    show = sub.add_parser("show", help="детали задачи")
    show.add_argument("id", type=int)
    show.set_defaults(func=cmd_show)

    cancel = sub.add_parser("cancel", help="отменить задачу")
    cancel.add_argument("id", type=int)
    cancel.set_defaults(func=cmd_cancel)

    confirm = sub.add_parser("confirm", help="подтвердить черновик (need_confirm → в работу)")
    confirm.add_argument("id", type=int)
    confirm.set_defaults(func=cmd_confirm)

    sub.add_parser("status", help="health демона").set_defaults(func=cmd_status)
    sub.add_parser("kinds", help="типы задач").set_defaults(func=cmd_kinds)
    sub.add_parser("metrics", help="метрики").set_defaults(func=cmd_metrics)

    events = sub.add_parser("events", help="журнал событий")
    events.add_argument("-n", "--limit", type=int, default=50)
    events.set_defaults(func=cmd_events)

    args = parser.parse_args()
    if not getattr(args, "func", None):
        parser.print_help()
        return 0
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
