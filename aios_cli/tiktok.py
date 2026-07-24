#!/usr/bin/env python3
"""AIOS CLI — TikTok platform commands."""

import json


def _add_tiktok_parsers(subparsers) -> None:
    """Register the ``tiktok`` subcommand tree."""
    tk = subparsers.add_parser("tiktok-shop", help="TikTok Shop platform commands")
    tk_sub = tk.add_subparsers(dest="tiktok_command")

    def with_db(p):
        p.add_argument("--db", default=None, help="SQLite database file")
        p.add_argument("--profile", default=None, help="Profile name")

    stats = tk_sub.add_parser("stats", help="Product statistics")
    stats.add_argument("--query", default=None)
    with_db(stats)

    tk_sub.add_parser("doctor", help="Environment readiness")

    # Price tracker
    pt = tk_sub.add_parser("price-tracker", help="Price drop detection")
    pt_sub = pt.add_subparsers(dest="price_command")
    p = pt_sub.add_parser("drops", help="Detect price drops")
    p.add_argument("--min-drop-pct", type=float, default=10.0)
    with_db(p)
    p = pt_sub.add_parser("track", help="Track product price")
    p.add_argument("--fingerprint", required=True)
    with_db(p)

    # Autowatch
    aw = tk_sub.add_parser("autowatch", help="AutoWatch cycle")
    aw.add_argument("--query", action="append", default=[])
    aw.add_argument("--no-collect", action="store_true")
    aw.add_argument("--min-drop-pct", type=float, default=10.0)
    with_db(aw)

    # Favorites
    fav = tk_sub.add_parser("favorites", help="Favorites management")
    fav_sp = fav.add_subparsers(dest="favorites_command")
    p = fav_sp.add_parser("add", help="Add to favorites")
    p.add_argument("--fingerprint", required=True)
    with_db(p)
    p = fav_sp.add_parser("remove", help="Remove from favorites")
    p.add_argument("--fingerprint", required=True)
    with_db(p)
    p = fav_sp.add_parser("list", help="List favorites")
    with_db(p)
    p = fav_sp.add_parser("drops", help="Check favorite price drops")
    p.add_argument("--min-drop-pct", type=float, default=10.0)
    with_db(p)


def _resolve_tiktok_db(args) -> str:
    """Resolve DB path."""
    if getattr(args, "db", None):
        return args.db
    return ":memory:"


def _run_tiktok(args) -> bool:
    """Dispatch TikTok subcommand."""
    from aios_core.modules.tiktok import TikTokStorage

    if args.tiktok_command == "stats":
        with TikTokStorage(_resolve_tiktok_db(args)) as storage:
            ads = storage.get_ads(query=args.query)
            print(json.dumps({"total_ads": len(ads), "query": args.query}, ensure_ascii=False, indent=2))
        return True

    if args.tiktok_command == "doctor":
        from aios_core.modules.tiktok import TikTokBootstrap
        report = TikTokBootstrap().doctor()
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return True

    if args.tiktok_command == "price-tracker":
        with TikTokStorage(_resolve_tiktok_db(args)) as storage:
            from aios_core.modules.tiktok import TikTokPriceTracker
            tracker = TikTokPriceTracker(storage)
            if args.price_command == "drops":
                alerts = tracker.detect_drops()
                print(json.dumps([a.to_dict() for a in alerts], ensure_ascii=False, indent=2))
            elif args.price_command == "track":
                stats = tracker.track_product(args.fingerprint)
                print(json.dumps(stats, ensure_ascii=False, indent=2))
        return True

    if args.tiktok_command == "autowatch":
        with TikTokStorage(_resolve_tiktok_db(args)) as storage:
            from aios_core.modules.tiktok import TikTokAutoWatch
            watcher = TikTokAutoWatch(storage)
            report = watcher.run_cycle(queries=args.query if args.query else None, collect=not args.no_collect)
            print(json.dumps(report, ensure_ascii=False, indent=2))
        return True

    if args.tiktok_command == "favorites":
        with TikTokStorage(_resolve_tiktok_db(args)) as storage:
            from aios_core.modules.tiktok import TikTokFavorites, TikTokPriceTracker
            tracker = TikTokPriceTracker(storage)
            fav = TikTokFavorites(storage, price_tracker=tracker)
            cmd = args.favorites_command
            if cmd == "add":
                print(json.dumps({"added": fav.add(args.fingerprint)}, indent=2))
            elif cmd == "remove":
                print(json.dumps({"removed": fav.remove(args.fingerprint)}, indent=2))
            elif cmd == "list":
                print(json.dumps({"favorites": fav.list_all()}, indent=2))
            elif cmd == "drops":
                print(json.dumps(fav.check_drops(), ensure_ascii=False, indent=2))
        return True

    return False
