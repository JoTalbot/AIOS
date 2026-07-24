#!/usr/bin/env python3
"""AIOS CLI — Rozetka.ua marketplace commands."""

import argparse
import json


def _add_rozetka_parsers(subparsers) -> None:
    """Register the ``rozetka`` subcommand tree."""
    rz = subparsers.add_parser("rozetka", help="Rozetka.ua marketplace commands")
    rz_sub = rz.add_subparsers(dest="rozetka_command")

    def with_db(p):
        """Add ``--db`` and ``--profile`` arguments."""
        p.add_argument("--db", default=None, help="SQLite database file")
        p.add_argument("--profile", default=None, help="Profile name from registry")

    stats = rz_sub.add_parser("stats", help="Product statistics")
    stats.add_argument("--query", default=None)
    with_db(stats)

    chats = rz_sub.add_parser("chats", help="List seller chat threads")
    with_db(chats)

    dm_send = rz_sub.add_parser("dm-send", help="Queue a seller chat reply")
    dm_send.add_argument("--chat", required=True, help="Chat key (e.g. chat:seller)")
    dm_send.add_argument("--text", required=True, help="Reply text")
    dm_send.add_argument("--auto-send", action="store_true", help="Send immediately (default: queue)")
    with_db(dm_send)

    dm_flush = rz_sub.add_parser("dm-flush", help="Flush pending outbox replies")
    with_db(dm_flush)

    dm_outbox = rz_sub.add_parser("dm-outbox", help="List pending reply drafts")
    with_db(dm_outbox)

    rz_sub.add_parser("doctor", help="Environment readiness checklist")

    # v9.6.0 — Price tracker
    price = rz_sub.add_parser("price-tracker", help="Price drop detection")
    price_sp = price.add_subparsers(dest="price_command")
    p = price_sp.add_parser("drops", help="Detect price drops")
    p.add_argument("--since", default=None, help="ISO timestamp to filter drops")
    p.add_argument("--min-drop-pct", type=float, default=5.0, help="Minimum drop percentage")
    p.add_argument("--min-abs-drop", type=float, default=1.0, help="Minimum absolute drop (UAH)")
    with_db(p)
    p = price_sp.add_parser("track", help="Track a specific product")
    p.add_argument("--fingerprint", required=True, help="Product fingerprint")
    with_db(p)

    # v9.6.0 — AutoWatch cycle
    aw = rz_sub.add_parser("autowatch", help="Full AutoWatch cycle")
    aw.add_argument("--query", action="append", default=[], help="Search queries to monitor")
    aw.add_argument("--min-drop-pct", type=float, default=5.0, help="Minimum price drop percentage for alerts")
    aw.add_argument("--min-age-days", type=float, default=3.0, help="Minimum days before marking stagnant")
    aw.add_argument("--max", type=int, default=50, help="Max cards to collect per query")
    aw.add_argument("--no-collect", action="store_true", help="Skip collection, only analyze")
    aw.add_argument("--webhook", default=None, help="Webhook URL for notifications")
    with_db(aw)

    # v9.6.0 — Favorites
    fav = rz_sub.add_parser("favorites", help="Favorite products management")
    fav_sp = fav.add_subparsers(dest="favorites_command")
    p = fav_sp.add_parser("add", help="Add product to favorites")
    p.add_argument("--fingerprint", required=True, help="Product fingerprint")
    with_db(p)
    p = fav_sp.add_parser("remove", help="Remove product from favorites")
    p.add_argument("--fingerprint", required=True, help="Product fingerprint")
    with_db(p)
    p = fav_sp.add_parser("list", help="List all favorites")
    p.add_argument("--details", action="store_true", help="Show details with price tracking")
    with_db(p)
    p = fav_sp.add_parser("drops", help="Check favorites for price drops")
    p.add_argument("--min-drop-pct", type=float, default=5.0, help="Minimum drop percentage")
    with_db(p)

    # v9.6.0 — Auto-login
    login = rz_sub.add_parser("auto-login", help="Auto-login scaffold")
    login_sp = login.add_subparsers(dest="login_command")
    p = login_sp.add_parser("check", help="Check login session status")
    p.add_argument("--serial", default=None, help="ADB device serial")
    with_db(p)
    p = login_sp.add_parser("attempt", help="Attempt auto-login")
    p.add_argument("--email", default=None, help="Login email")
    p.add_argument("--password", default=None, help="Login password")
    p.add_argument("--serial", default=None, help="ADB device serial")
    with_db(p)


def _resolve_rozetka_db(args) -> str:
    """Resolve DB path for rozetka command."""
    from aios_core.platforms import Profile, resolve_profile

    if getattr(args, "db", None):
        return args.db
    profile = resolve_profile("rozetka", getattr(args, "profile", None))
    return profile.db_path


def _run_rozetka(args) -> bool:
    """Dispatch a Rozetka subcommand.

    Returns True if the command was recognized and executed, False otherwise.
    """
    from aios_core.modules.rozetka import RozetkaStorage

    if args.rozetka_command == "stats":
        with RozetkaStorage(_resolve_rozetka_db(args)) as storage:
            ads = storage.get_ads(query=args.query)
            print(json.dumps({
                "total_ads": len(ads),
                "query": args.query,
            }, ensure_ascii=False, indent=2))
        return True

    if args.rozetka_command == "chats":
        with RozetkaStorage(_resolve_rozetka_db(args)) as storage:
            threads = storage.outbox_list()
            print(json.dumps(threads, ensure_ascii=False, indent=2))
        return True

    if args.rozetka_command == "dm-send":
        with RozetkaStorage(_resolve_rozetka_db(args)) as storage:
            from aios_core.modules.rozetka import RozetkaMessenger
            messenger = RozetkaMessenger(storage=storage)
            result = messenger.send_reply(args.chat, args.text)
            print(json.dumps(result, ensure_ascii=False, indent=2))
        return True

    if args.rozetka_command == "dm-flush":
        with RozetkaStorage(_resolve_rozetka_db(args)) as storage:
            from aios_core.modules.rozetka import RozetkaMessenger
            messenger = RozetkaMessenger(storage=storage)
            flushed = messenger.flush_outbox()
            print(json.dumps(flushed, ensure_ascii=False, indent=2))
        return True

    if args.rozetka_command == "dm-outbox":
        with RozetkaStorage(_resolve_rozetka_db(args)) as storage:
            print(json.dumps(storage.outbox_list(), ensure_ascii=False, indent=2))
        return True

    if args.rozetka_command == "doctor":
        from aios_core.modules.rozetka import RozetkaBootstrap
        report = RozetkaBootstrap().doctor()
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return True

    # v9.6.0 — Price tracker commands
    if args.rozetka_command == "price-tracker":
        with RozetkaStorage(_resolve_rozetka_db(args)) as storage:
            from aios_core.modules.rozetka import RozetkaPriceTracker
            tracker = RozetkaPriceTracker(
                storage,
                min_drop_pct=getattr(args, "min_drop_pct", 5.0),
                min_absolute_drop=getattr(args, "min_abs_drop", 1.0),
            )
            if getattr(args, "price_command", None) == "drops":
                alerts = tracker.detect_drops(since=getattr(args, "since", None))
                print(json.dumps([a.to_dict() for a in alerts], ensure_ascii=False, indent=2))
            elif getattr(args, "price_command", None) == "track":
                stats = tracker.track_product(args.fingerprint)
                print(json.dumps(stats, ensure_ascii=False, indent=2))
            else:
                print(json.dumps({"error": "unknown price-tracker subcommand"}, indent=2))
        return True

    # v9.6.0 — AutoWatch cycle
    if args.rozetka_command == "autowatch":
        with RozetkaStorage(_resolve_rozetka_db(args)) as storage:
            from aios_core.modules.rozetka import RozetkaAutoWatch
            watcher = RozetkaAutoWatch(
                storage,
                min_drop_pct=getattr(args, "min_drop_pct", 5.0),
                max_cards=getattr(args, "max", 50),
                min_age_days=getattr(args, "min_age_days", 3.0),
            )
            report = watcher.run_cycle(
                queries=args.query if args.query else None,
                collect=not getattr(args, "no_collect", False),
            )
            print(json.dumps(report, ensure_ascii=False, indent=2))
        return True

    # v9.6.0 — Favorites commands
    if args.rozetka_command == "favorites":
        with RozetkaStorage(_resolve_rozetka_db(args)) as storage:
            from aios_core.modules.rozetka import RozetkaFavorites, RozetkaPriceTracker
            tracker = RozetkaPriceTracker(
                storage, min_drop_pct=getattr(args, "min_drop_pct", 5.0)
            )
            fav = RozetkaFavorites(storage, price_tracker=tracker)
            cmd = getattr(args, "favorites_command", None)
            if cmd == "add":
                result = fav.add(args.fingerprint)
                print(json.dumps({"added": result, "fingerprint": args.fingerprint}, indent=2))
            elif cmd == "remove":
                result = fav.remove(args.fingerprint)
                print(json.dumps({"removed": result, "fingerprint": args.fingerprint}, indent=2))
            elif cmd == "list":
                if getattr(args, "details", False):
                    items = fav.list_with_details()
                    print(json.dumps(items, ensure_ascii=False, indent=2))
                else:
                    fps = fav.list_all()
                    print(json.dumps({"favorites": fps}, indent=2))
            elif cmd == "drops":
                drops = fav.check_drops()
                print(json.dumps(drops, ensure_ascii=False, indent=2))
            else:
                print(json.dumps({"error": "unknown favorites subcommand"}, indent=2))
        return True

    # v9.6.0 — Auto-login commands
    if args.rozetka_command == "auto-login":
        from aios_core.modules.rozetka import RozetkaAutoLogin
        auto = RozetkaAutoLogin()
        cmd = getattr(args, "login_command", None)
        if cmd == "check":
            result = auto.check_session()
            print(json.dumps(result, ensure_ascii=False, indent=2))
        elif cmd == "attempt":
            result = auto.attempt_login(
                email=getattr(args, "email", None),
                password=getattr(args, "password", None),
            )
            print(json.dumps({
                "state": result.state.value,
                "message": result.message,
                "timestamp": result.timestamp,
            }, ensure_ascii=False, indent=2))
        else:
            print(json.dumps({"error": "unknown auto-login subcommand"}, indent=2))
        return True

    return False
