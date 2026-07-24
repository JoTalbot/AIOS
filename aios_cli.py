#!/usr/bin/env python3
"""
AIOS Command Line Interface v4.1 — Entry Point.

Sub-commands delegated to:
- aios_cli.olx (OLX parser agent)
- aios_cli.platforms (platforms, profiles, devices, shards, cron-plan)
- aios_cli.instagram (Instagram agent)
- aios_cli.messengers (WhatsApp, Viber, Facebook)
"""

import argparse
import json

import uvicorn

from aios_core import Database, Orchestrator
from aios_core.dashboard import create_dashboard
from aios_cli.olx import _add_olx_parsers, _run_olx
from aios_cli.rozetka import _add_rozetka_parsers, _run_rozetka
from aios_cli.platforms import (
    _run_platforms, _run_profiles, _run_devices, _run_shards, _run_cron_plan,
)
from aios_cli.instagram import _run_instagram, _adb_dump_driver
from aios_cli.messengers import _run_msg_platform

DEFAULT_OLX_DB = "olx_ads.sqlite"


def _add_all_subparsers(subparsers):
    """Register all command-line subparsers."""

    # Run server
    p = subparsers.add_parser("run", help="Run REST API")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8000)

    # Dashboard
    p = subparsers.add_parser("dashboard", help="Run Web Dashboard")
    p.add_argument("--port", type=int, default=8080)

    subparsers.add_parser("demo", help="Run v4.1 demo")
    subparsers.add_parser("stats", help="Show system stats")

    # Platforms
    plat = subparsers.add_parser("platforms", help="Manage marketplace platforms")
    ps = plat.add_subparsers(dest="platforms_command")
    ps.add_parser("list")
    p = ps.add_parser("scaffold", help="Generate platform skeleton")
    p.add_argument("--name", required=True); p.add_argument("--package", required=True)
    p.add_argument("--description", default=""); p.add_argument("--locale", default="uk-UA")
    p.add_argument("--root", default="."); p.add_argument("--dry-run", action="store_true")
    p = ps.add_parser("from-apk"); p.add_argument("apk")
    p.add_argument("--name", default=None); p.add_argument("--locale", default="uk-UA")
    p.add_argument("--root", default="."); p.add_argument("--dry-run", action="store_true")
    p = ps.add_parser("calibrate"); p.add_argument("--platform", required=True)
    p.add_argument("--dump", required=True); p.add_argument("--detail", default=None)
    p.add_argument("--messages", default=None); p.add_argument("--navigation", default=None)
    p.add_argument("--write", action="store_true"); p.add_argument("--root", default=".")
    p = ps.add_parser("reels"); p.add_argument("--platform", required=True)
    p.add_argument("--profile", default=None); p.add_argument("--db", default=None)
    p.add_argument("--max", type=int, default=100, dest="max_cards")
    p.add_argument("--serial", default=None); p.add_argument("--directory", default="platforms")
    p.add_argument("--open-tab", action="store_true"); p.add_argument("--webhook", default=None)
    p = ps.add_parser("doctor"); p.add_argument("--platform", required=True)
    p.add_argument("--serial", default=None); p.add_argument("--directory", default="platforms")
    p.add_argument("--calibrate-recipe", action="store_true")
    p = ps.add_parser("fetch-apk"); p.add_argument("package")
    p.add_argument("--out", default="apks"); p.add_argument("--source", default="apkpure")
    p = ps.add_parser("autowatch"); p.add_argument("--platform", required=True)
    p.add_argument("--profile", default=None); p.add_argument("--query", action="append", default=[])
    p.add_argument("--max", type=int, default=50); p.add_argument("--webhook", default=None)
    p.add_argument("--drive", choices=["none","point","login"], default="none")
    p.add_argument("--no-collect", action="store_true")
    p = ps.add_parser("marker-check"); p.add_argument("--platform", required=True)
    p.add_argument("--dump", required=True)
    p = ps.add_parser("codegen"); p.add_argument("--platform", required=True)
    p.add_argument("--root", default="."); p.add_argument("--dry-run", action="store_true")
    p.add_argument("--force", action="store_true")
    p = ps.add_parser("bootup"); p.add_argument("--apk", default=None)
    p.add_argument("--name", default=None); p.add_argument("--package", default=None)
    p.add_argument("--dump", default=None); p.add_argument("--query", default=None)
    p.add_argument("--fetch", action="store_true"); p.add_argument("--apks-dir", default="apks")
    p.add_argument("--serial", default=None); p.add_argument("--lease", action="store_true")
    p.add_argument("--locale", default="uk-UA"); p.add_argument("--root", default=".")
    p.add_argument("--dry-run", action="store_true")

    # Onboard
    p = subparsers.add_parser("onboard"); p.add_argument("apk", nargs="?", default=None)
    p.add_argument("--name", default=None); p.add_argument("--package", default=None)
    p.add_argument("--root", default="."); p.add_argument("--no-fetch", action="store_true")
    p.add_argument("--apks-dir", default="apks", dest="apks_dir")
    p.add_argument("--dump", default=None); p.add_argument("--query", default=None)
    p.add_argument("--serial", default=None); p.add_argument("--dry-run", action="store_true")

    # Messengers (WhatsApp, Viber, Facebook)
    for app in ("whatsapp", "viber", "facebook"):
        ap = subparsers.add_parser(app, help=f"{app} messenger")
        aps = ap.add_subparsers(dest="messenger_command")
        aps.add_parser("doctor")
        for cmd in ("chats", "dm-send", "dm-flush", "dm-outbox"):
            c = aps.add_parser(cmd)
            if cmd == "dm-send": c.add_argument("--chat", required=True); c.add_argument("--text", required=True); c.add_argument("--auto-send", action="store_true")
            c.add_argument("--db", default=None); c.add_argument("--serial", default=None); c.add_argument("--directory", default="platforms")

    # Instagram
    ig = subparsers.add_parser("instagram")
    igs = ig.add_subparsers(dest="instagram_command")
    igs.add_parser("doctor")
    for cmd, args in [("collect", [("--query",None),("--max",100)]),("dm-send",[("--chat",True),("--text",True),("--auto-send",False)]),("dm-flush",[]),("dm-outbox",[]),("login-drive",[("--query",None)]),("own",[("--dump",None)]),("post",[("--image",True),("--text",True),("--confirm",False)]),("reels",[("--max",100),("--open-tab",False),("--webhook",None)]),("autopilot",[("--query",None),("--max",100),("--reels-max",50),("--login",False),("--open-tab",False),("--webhook",None),("--post-image",None),("--post-text",None),("--own",False),("--own-dump",None),("--pace-actions",None),("--pace-jitter",None),("--promote",False),("--promote-budget",None),("--promote-min-age-days",None),("--confirm",False)])]:
        c = igs.add_parser(cmd)
        for an, av in args: c.add_argument(an, type=int if isinstance(av, int) and not isinstance(av, bool) else None, default=av) if av is not False else c.add_argument(an, action="store_true")
    for cmd in ["collect","dm-send","dm-flush","dm-outbox","own","reels","autopilot","post"]:
        igs.choices[cmd].add_argument("--db", default="data/instagram.sqlite") if cmd in igs.choices else None
        if cmd in igs.choices: igs.choices[cmd].add_argument("--serial", default=None); igs.choices[cmd].add_argument("--directory", default="platforms")

    # Profiles
    prof = subparsers.add_parser("profiles"); ps2 = prof.add_subparsers(dest="profiles_command")
    p = ps2.add_parser("list"); p.add_argument("--platform", default=None)
    p = ps2.add_parser("add"); p.add_argument("--platform", required=True); p.add_argument("--name", required=True)
    p.add_argument("--device", default=None); p.add_argument("--db", default=None)
    p.add_argument("--android-user", type=int, default=0); p.add_argument("--locale", default="uk-UA")
    p.add_argument("--notes", default=""); p.add_argument("--default", action="store_true")
    for c in ("show","remove","set-default"):
        p = ps2.add_parser(c); p.add_argument("--platform", required=True); p.add_argument("--name", required=True)

    # Shards
    sh = subparsers.add_parser("shards"); ss = sh.add_subparsers(dest="shards_command")
    ss.add_parser("list"); p = ss.add_parser("add"); p.add_argument("--host", required=True); p.add_argument("--base-url", required=True)
    p = ss.add_parser("remove"); p.add_argument("--host", required=True)
    for c in ("route","unroute"): p = ss.add_parser(c); p.add_argument("--profile", required=True)
    p = ss.add_parser("monitor"); p.add_argument("--interval", type=float, default=30.0); p.add_argument("--once", action="store_true")
    p = ss.add_parser("jobs"); p.add_argument("--status", default=None); p.add_argument("--stats", action="store_true"); p.add_argument("--ttl", type=float, default=600)
    p = ss.add_parser("requeue-stale"); p.add_argument("--ttl", type=float, default=600)
    p = ss.add_parser("enqueue"); p.add_argument("--profile", required=True); p.add_argument("--kind", required=True); p.add_argument("--payload", default=None)
    p = ss.add_parser("work"); p.add_argument("--host", required=True); p.add_argument("--once", action="store_true"); p.add_argument("--interval", type=float, default=30.0)

    # Cron-plan
    p = subparsers.add_parser("cron-plan"); p.add_argument("--platform", default="olx"); p.add_argument("--interval", type=int, default=15)
    p.add_argument("--webhook", default=None); p.add_argument("--write", default=None)
    p.add_argument("--with-marker-check", action="store_true"); p.add_argument("--shard-map", action="store_true"); p.add_argument("--via-shards", action="store_true")

    # Devices
    dev = subparsers.add_parser("devices"); ds = dev.add_subparsers(dest="devices_command")
    ds.add_parser("list"); p = ds.add_parser("register"); p.add_argument("--serial", required=True); p.add_argument("--avd", default=None)
    p = ds.add_parser("lease"); p.add_argument("--profile", required=True); p.add_argument("--serial", default=None); p.add_argument("--enqueue", action="store_true"); p.add_argument("--priority", type=int, default=0); p.add_argument("--sync", action="store_true")
    ds.add_parser("waitlist"); p = ds.add_parser("enqueue"); p.add_argument("--profile", required=True); p.add_argument("--priority", type=int, default=0)
    p = ds.add_parser("cancel-wait"); p.add_argument("--profile", required=True)
    p = ds.add_parser("release"); p.add_argument("--profile", required=True)
    p = ds.add_parser("heartbeat"); p.add_argument("--serial", required=True)
    p = ds.add_parser("reap"); p.add_argument("--max-silence-s", type=float, default=900.0)
    p = ds.add_parser("ensure"); p.add_argument("--profile", required=True); p.add_argument("--avd-prefix", default="aios")
    p = ds.add_parser("monitor"); p.add_argument("--interval", type=float, default=30.0); p.add_argument("--once", action="store_true"); p.add_argument("--reap-after-s", type=float, default=900.0)
    p = ds.add_parser("fleet-run"); p.add_argument("--every-s", type=float, default=900.0); p.add_argument("--query", action="append", default=[]); p.add_argument("--webhook", default=None)
    p = ds.add_parser("limits"); p.add_argument("--set", dest="set_limit", default=None, metavar="KEY=VALUE")

    # Admin
    adm = subparsers.add_parser("admin"); adms = adm.add_subparsers(dest="admin_command")
    p = adms.add_parser("export"); p.add_argument("--type", choices=["tasks","memory","audit","knowledge","all"], default="all")
    p.add_argument("--format", choices=["json","csv"], default="json"); p.add_argument("--output","-o", default="./export")
    p.add_argument("--since", default=None); p.add_argument("--limit", type=int, default=None); p.add_argument("--db", default="aios.sqlite")
    p = adms.add_parser("import"); p.add_argument("--type", choices=["tasks"], default="tasks"); p.add_argument("--format", choices=["json","csv"], default="json")
    p.add_argument("--input","-i", required=True); p.add_argument("--db", default="aios.sqlite")
    keys = adms.add_parser("keys"); ks = keys.add_subparsers(dest="keys_command")
    p = ks.add_parser("generate"); p.add_argument("--subject", required=True); p.add_argument("--roles", nargs="+", default=["viewer"]); p.add_argument("--ttl", type=int, default=None); p.add_argument("--prefix", default="aios")
    p = ks.add_parser("list"); p.add_argument("--subject", default=None)
    p = ks.add_parser("revoke"); p.add_argument("--key", required=True); p.add_argument("--reason", default="")
    p = ks.add_parser("rotate"); p.add_argument("--key", required=True); p.add_argument("--ttl", type=int, default=None); p.add_argument("--reason", default="rotation")
    ks.add_parser("health")
    bu = adms.add_parser("backup"); bs = bu.add_subparsers(dest="backup_command")
    for cmd, extra_args in [("create",[("--label",""),("--mode","full")]),("list",[]),("verify",[("--backup-id",True)]),("restore",[("--backup-id",True),("--target",None)]),("cleanup",[]),("health",[])]:
        p = bs.add_parser(cmd)
        for an, av in extra_args:
            if av is True: p.add_argument(an, required=True)
            elif av is not None: p.add_argument(an, default=av)
        p.add_argument("--db", default="aios.sqlite"); p.add_argument("--backup-dir", default="./backups")
    wh = adms.add_parser("webhooks"); ws = wh.add_subparsers(dest="webhooks_command")
    p = ws.add_parser("register"); p.add_argument("--name", required=True); p.add_argument("--url", required=True); p.add_argument("--events", nargs="+", required=True); p.add_argument("--secret", default=None)
    ws.add_parser("list"); p = ws.add_parser("test"); p.add_argument("--name", required=True)
    p = ws.add_parser("notify"); p.add_argument("--event", required=True); p.add_argument("--data", default=None); p.add_argument("--severity", choices=["info","warning","critical"], default="info")
    ws.add_parser("health")

    # OLX
    _add_olx_parsers(subparsers)

    # Rozetka
    _add_rozetka_parsers(subparsers)


def main(argv=None):
    """AIOS CLI entry point — parse args and dispatch to sub-command handlers."""
    parser = argparse.ArgumentParser(description="AIOS CLI")
    subparsers = parser.add_subparsers(dest="command")
    _add_all_subparsers(subparsers)

    args = parser.parse_args(argv)

    if args.command == "run":
        from run_rest_api import main as run_main
        run_main()
    elif args.command == "dashboard":
        from aios_core.container import container as _c
        db = _c.db()
        orch = _c.orchestrator()
        app = create_dashboard(orch)
        print(f"Starting Dashboard on http://127.0.0.1:{args.port}")
        uvicorn.run(app, host="127.0.0.1", port=args.port)
    elif args.command == "demo":
        from demo_v41 import main as demo_main
        demo_main()
    elif args.command == "stats":
        db = _c.db()
        orch = _c.orchestrator()
        print(json.dumps(orch.stats(), indent=2))
    elif args.command == "platforms":
        if not _run_platforms(args): parser.parse_args(["platforms", "--help"])
    elif args.command == "onboard":
        from aios_core.platforms.onboard import onboard_package
        try:
            report = onboard_package(
                apk=getattr(args, "apk", None), name=getattr(args, "name", None),
                package=getattr(args, "package", None), project_root=getattr(args, "root", "."),
                fetch=not getattr(args, "no_fetch", False),
                apks_dir=getattr(args, "apks_dir", "apks"),
                dump_path=getattr(args, "dump", None),
                query=getattr(args, "query", None),
                serial=getattr(args, "serial", None),
                driver=None if getattr(args, "serial", None) is None else _adb_dump_driver(args.serial),
                dry_run=getattr(args, "dry_run", False),
            )
        except ValueError as exc:
            print(json.dumps({"error": str(exc)}, ensure_ascii=False))
            return
        print(json.dumps(report, ensure_ascii=False, indent=2))
    elif args.command in ("whatsapp", "viber", "facebook"):
        if not _run_msg_platform(args, args.command): parser.parse_args([args.command, "--help"])
    elif args.command == "instagram":
        if not _run_instagram(args): parser.parse_args(["instagram", "--help"])
    elif args.command == "profiles":
        if not _run_profiles(args): parser.parse_args(["profiles", "--help"])
    elif args.command == "shards":
        if not _run_shards(args): parser.parse_args(["shards", "--help"])
    elif args.command == "cron-plan":
        if not _run_cron_plan(args): parser.parse_args(["cron-plan", "--help"])
    elif args.command == "devices":
        try: handled = _run_devices(args)
        except ValueError as exc: print(json.dumps({"error": str(exc)}, ensure_ascii=False)); handled = True
        if not handled: parser.parse_args(["devices", "--help"])
    elif args.command == "olx":
        try: handled = _run_olx(args)
        except ValueError as exc: print(json.dumps({"error": str(exc)}, ensure_ascii=False)); handled = True
        if not handled: parser.parse_args(["olx", "--help"])
    elif args.command == "rozetka":
        try: handled = _run_rozetka(args)
        except ValueError as exc: print(json.dumps({"error": str(exc)}, ensure_ascii=False)); handled = True
        if not handled: parser.parse_args(["rozetka", "--help"])
    elif args.command == "admin":
        from aios_cli_admin import (
            run_backup_cleanup, run_backup_create, run_backup_health,
            run_backup_list, run_backup_restore, run_backup_verify,
            run_export, run_import, run_keys_generate, run_keys_health,
            run_keys_list, run_keys_revoke, run_keys_rotate,
            run_webhooks_health, run_webhooks_list, run_webhooks_notify,
            run_webhooks_register, run_webhooks_test,
        )
        cmd_map = {
            "export": run_export, "import": run_import,
            "keys": lambda a: {
                "generate": run_keys_generate, "list": run_keys_list,
                "revoke": run_keys_revoke, "rotate": run_keys_rotate,
                "health": run_keys_health,
            }.get(getattr(a, "keys_command", ""), lambda x: adm.parse_args(["keys", "--help"]))(a),
            "backup": lambda a: {
                "create": run_backup_create, "list": run_backup_list,
                "verify": run_backup_verify, "restore": run_backup_restore,
                "cleanup": run_backup_cleanup, "health": run_backup_health,
            }.get(getattr(a, "backup_command", ""), lambda x: adm.parse_args(["backup", "--help"]))(a),
            "webhooks": lambda a: {
                "register": run_webhooks_register, "list": run_webhooks_list,
                "test": run_webhooks_test, "notify": run_webhooks_notify,
                "health": run_webhooks_health,
            }.get(getattr(a, "webhooks_command", ""), lambda x: adm.parse_args(["webhooks", "--help"]))(a),
        }
        cmd_map.get(args.admin_command, lambda x: adm.parse_args(["--help"]))(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
