#!/usr/bin/env python3
"""
AIOS Command Line Interface v4.1
"""

import argparse
import asyncio
import json
from aios_core import Orchestrator, Database
from aios_core.dashboard import create_dashboard
import uvicorn

DEFAULT_OLX_DB = "olx_ads.sqlite"


def _add_olx_parsers(subparsers) -> None:
    olx_parser = subparsers.add_parser("olx", help="OLX Parser Agent commands")
    olx_sub = olx_parser.add_subparsers(dest="olx_command")

    def with_db(p):
        p.add_argument("--db", default=DEFAULT_OLX_DB, help="SQLite database file")

    collect = olx_sub.add_parser("collect", help="Collect ads via ADB")
    collect.add_argument("--query", required=True, help="Search query")
    collect.add_argument("--max-cards", type=int, default=50)
    with_db(collect)

    stats = olx_sub.add_parser("stats", help="Market statistics")
    stats.add_argument("--query", default=None)
    with_db(stats)

    recommend = olx_sub.add_parser("recommend", help="Listing recommendations")
    recommend.add_argument("--query", default=None)
    recommend.add_argument("--title", default=None)
    recommend.add_argument("--price", type=float, default=None)
    with_db(recommend)

    export = olx_sub.add_parser("export", help="Export ads to CSV/JSON")
    export.add_argument("--query", default=None)
    export.add_argument("--format", choices=["csv", "json"], default="json")
    export.add_argument("--output", default=None, help="Output file (default: stdout)")
    with_db(export)

    history = olx_sub.add_parser("history", help="Price history of one ad")
    history.add_argument("--fingerprint", required=True)
    with_db(history)

    drops = olx_sub.add_parser("drops", help="Price drops & gone-from-feed ads")
    drops.add_argument("--query", default=None)
    with_db(drops)


def _run_olx(args) -> bool:
    from aios_core.modules.olx import (
        CollectionScheduler,
        CompetitorAnalyzer,
        OLXCollector,
        OLXStorage,
        PriceTracker,
        RecommendationEngine,
    )

    if args.olx_command == "collect":
        with OLXStorage(args.db) as storage:
            scheduler = CollectionScheduler(
                collector=OLXCollector(), storage=storage
            )
            summaries = scheduler.run_once([args.query], max_cards=args.max_cards)
            print(json.dumps(summaries, ensure_ascii=False, indent=2))
        return True

    if args.olx_command == "stats":
        with OLXStorage(args.db) as storage:
            ads = storage.get_ads(query=args.query)
            report = CompetitorAnalyzer().analyze(ads, query=args.query)
            print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2))
        return True

    if args.olx_command == "recommend":
        from aios_core.modules.olx import AdCard

        my_ad = None
        if args.title is not None or args.price is not None:
            my_ad = AdCard(
                title=args.title or "", price=args.price,
                currency="UAH", query=args.query,
            )
        with OLXStorage(args.db) as storage:
            ads = storage.get_ads(query=args.query)
            advice = RecommendationEngine().recommend(ads, my_ad=my_ad)
            print(advice.to_text())
        return True

    if args.olx_command == "export":
        with OLXStorage(args.db) as storage:
            if args.format == "json":
                payload = storage.export_json(query=args.query)
            else:
                payload = storage.export_csv(query=args.query)
        if args.output:
            with open(args.output, "w", encoding="utf-8") as fh:
                fh.write(payload)
            print(f"Exported to {args.output}")
        else:
            print(payload)
        return True

    if args.olx_command == "history":
        with OLXStorage(args.db) as storage:
            print(json.dumps(
                storage.price_history(args.fingerprint),
                ensure_ascii=False, indent=2,
            ))
        return True

    if args.olx_command == "drops":
        with OLXStorage(args.db) as storage:
            tracker = PriceTracker(storage)
            result = {
                "drops": [change.to_dict() for change in tracker.price_drops(query=args.query)],
                "gone": [ad.to_dict() for ad in tracker.gone_from_feed(query=args.query)],
            }
            print(json.dumps(result, ensure_ascii=False, indent=2))
        return True

    return False


def main(argv=None):
    parser = argparse.ArgumentParser(description="AIOS CLI")
    subparsers = parser.add_subparsers(dest="command")

    # Run server
    run_parser = subparsers.add_parser("run", help="Run REST API")
    run_parser.add_argument("--host", default="127.0.0.1")
    run_parser.add_argument("--port", type=int, default=8000)

    # Run dashboard
    dash_parser = subparsers.add_parser("dashboard", help="Run Web Dashboard")
    dash_parser.add_argument("--port", type=int, default=8080)

    # Demo
    subparsers.add_parser("demo", help="Run v4.1 demo")

    # Stats
    subparsers.add_parser("stats", help="Show system stats")

    # OLX Parser Agent
    _add_olx_parsers(subparsers)

    args = parser.parse_args(argv)

    if args.command == "run":
        from run_rest_api import main as run_main
        run_main()
    elif args.command == "dashboard":
        db = Database("aios.sqlite")
        orch = Orchestrator(db=db)
        app = create_dashboard(orch)
        print(f"Starting Dashboard on http://127.0.0.1:{args.port}")
        uvicorn.run(app, host="127.0.0.1", port=args.port)
    elif args.command == "demo":
        from demo_v41 import main as demo_main
        demo_main()
    elif args.command == "stats":
        db = Database("aios.sqlite")
        orch = Orchestrator(db=db)
        print(json.dumps(orch.stats(), indent=2))
    elif args.command == "olx":
        if not _run_olx(args):
            parser.parse_args(["olx", "--help"])
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
