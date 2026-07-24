#!/usr/bin/env python3
"""AIOS CLI — Facebook Marketplace commands."""

import json


def _add_facebook_parsers(subparsers) -> None:
    """Register the ``facebook`` subcommand tree."""
    fb = subparsers.add_parser("fb-marketplace", help="Facebook Marketplace commands")
    fb_sub = fb.add_subparsers(dest="facebook_command")

    def with_db(p):
        p.add_argument("--db", default=None, help="SQLite database file")
        p.add_argument("--profile", default=None)

    stats = fb_sub.add_parser("stats", help="Product statistics")
    stats.add_argument("--query", default=None)
    with_db(stats)

    fb_sub.add_parser("doctor", help="Environment readiness")

    # Price tracker
    pt = fb_sub.add_parser("price-tracker", help="Price drop detection")
    pt_sub = pt.add_subparsers(dest="price_command")
    p = pt_sub.add_parser("drops", help="Detect price drops")
    with_db(p)
    p = pt_sub.add_parser("track", help="Track product price")
    p.add_argument("--fingerprint", required=True)
    with_db(p)

    # Autowatch
    aw = fb_sub.add_parser("autowatch", help="AutoWatch cycle")
    aw.add_argument("--query", action="append", default=[])
    aw.add_argument("--no-collect", action="store_true")
    with_db(aw)

    # Favorites
    fav = fb_sub.add_parser("favorites", help="Favorites management")
    fav_sp = fav.add_subparsers(dest="favorites_command")
    p = fav_sp.add_parser("add", help="Add to favorites")
    p.add_argument("--fingerprint", required=True)
    with_db(p)
    p = fav_sp.add_parser("list", help="List favorites")
    with_db(p)


def _resolve_facebook_db(args) -> str:
    """Resolve DB path."""
    if getattr(args, "db", None):
        return args.db
    return ":memory:"


def _run_facebook(args) -> bool:
    """Dispatch Facebook subcommand."""
    from aios_core.modules.facebook import FacebookStorage

    if args.facebook_command == "stats":
        with FacebookStorage(_resolve_facebook_db(args)) as storage:
            ads = storage.get_ads(query=args.query)
            print(json.dumps({"total_ads": len(ads), "query": args.query}, ensure_ascii=False, indent=2))
        return True

    if args.facebook_command == "doctor":
        from aios_core.modules.facebook import FacebookBootstrap
        report = FacebookBootstrap().doctor()
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return True

    if args.facebook_command == "price-tracker":
        with FacebookStorage(_resolve_facebook_db(args)) as storage:
            from aios_core.modules.facebook import FacebookPriceTracker
            tracker = FacebookPriceTracker(storage)
            if args.price_command == "drops":
                alerts = tracker.detect_drops()
                print(json.dumps([a.to_dict() for a in alerts], ensure_ascii=False, indent=2))
            elif args.price_command == "track":
                stats = tracker.track_product(args.fingerprint)
                print(json.dumps(stats, ensure_ascii=False, indent=2))
        return True

    if args.facebook_command == "autowatch":
        with FacebookStorage(_resolve_facebook_db(args)) as storage:
            from aios_core.modules.facebook import FacebookAutoWatch
            watcher = FacebookAutoWatch(storage)
            report = watcher.run_cycle(queries=args.query if args.query else None, collect=not args.no_collect)
            print(json.dumps(report, ensure_ascii=False, indent=2))
        return True

    if args.facebook_command == "favorites":
        with FacebookStorage(_resolve_facebook_db(args)) as storage:
            from aios_core.modules.facebook import FacebookFavorites
            fav = FacebookFavorites(storage)
            cmd = args.favorites_command
            if cmd == "add":
                print(json.dumps({"added": fav.add(args.fingerprint)}, indent=2))
            elif cmd == "list":
                print(json.dumps({"favorites": fav.list_all()}, indent=2))
        return True

    return False
