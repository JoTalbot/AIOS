#!/usr/bin/env python3
"""
AIOS Command Line Interface v4.1
"""

import argparse
import asyncio
import json
from pathlib import Path
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

    detail = olx_sub.add_parser("detail", help="Parse an ad detail page dump")
    detail.add_argument("--xml", required=True, help="UIAutomator XML dump")
    with_db(detail)

    chats = olx_sub.add_parser("chats", help="List personal chat threads (ADB)")
    with_db(chats)

    reply = olx_sub.add_parser("reply", help="Queue/send a chat reply")
    reply.add_argument("--chat-key", required=True)
    reply.add_argument("--text", required=True)
    reply.add_argument("--interlocutor", default=None)
    reply.add_argument("--send-now", action="store_true", help="Send immediately (default: queue)")
    with_db(reply)

    outbox = olx_sub.add_parser("outbox", help="List pending reply drafts")
    outbox.add_argument("--status", default=None)
    with_db(outbox)

    own = olx_sub.add_parser("own", help="Own listings: list / snapshot / stagnant")
    own.add_argument("--xml", default=None, help="Parse 'My listings' XML dump and record snapshot")
    own.add_argument("--stagnant", action="store_true", help="Show stagnant listings")
    own.add_argument("--min-age-days", type=float, default=3.0)
    own.add_argument("--min-views-per-day", type=float, default=1.0)
    with_db(own)

    improve = olx_sub.add_parser("improve", help="Improvement suggestion for an own ad")
    improve.add_argument("--fingerprint", required=True)
    improve.add_argument("--query", default=None, help="Competitor query for comparison")
    with_db(improve)

    repost = olx_sub.add_parser("repost", help="Repost plan (dry-run) or execute")
    repost.add_argument("--fingerprint", required=True)
    repost.add_argument("--confirm", action="store_true", help="Execute on device (default: dry-run)")
    with_db(repost)

    subscribe = olx_sub.add_parser("subscribe", help="Add a search subscription")
    subscribe.add_argument("--query", required=True)
    subscribe.add_argument("--name", default=None)
    subscribe.add_argument("--min-price", type=float, default=None)
    subscribe.add_argument("--max-price", type=float, default=None)
    subscribe.add_argument("--city", default=None)
    with_db(subscribe)

    subs = olx_sub.add_parser("subscriptions", help="List search subscriptions")
    with_db(subs)

    favorite = olx_sub.add_parser("favorite", help="Add/remove a favorite ad")
    favorite.add_argument("--fingerprint", required=True)
    favorite.add_argument("--remove", action="store_true")
    with_db(favorite)

    favorites = olx_sub.add_parser("favorites", help="List favorites and their drops")
    favorites.add_argument("--alerts", action="store_true")
    with_db(favorites)

    autowatch = olx_sub.add_parser("autowatch", help="Run one full AutoWatch cycle")
    autowatch.add_argument("--query", action="append", default=[],
                           help="Search query to collect (repeatable)")
    autowatch.add_argument("--no-collect", action="store_true")
    autowatch.add_argument("--max-cards", type=int, default=50)
    autowatch.add_argument("--webhook", default=None)
    autowatch.add_argument("--chat-id", default=None)
    with_db(autowatch)

    profile = olx_sub.add_parser("profile", help="Profile: show stored / parse dump")
    profile.add_argument("--xml", default=None, help="Profile screen XML dump")
    profile.add_argument("--settings", action="store_true", help="Also parse settings toggles")
    with_db(profile)

    profile_edit = olx_sub.add_parser("profile-edit", help="Edit a profile field")
    profile_edit.add_argument("--field", required=True)
    profile_edit.add_argument("--value", required=True)
    profile_edit.add_argument("--confirm", action="store_true")
    with_db(profile_edit)

    competitive = olx_sub.add_parser("competitive", help="Competitor surveillance by own ads")
    competitive.add_argument("--fingerprint", default=None, help="Report for one own ad")
    with_db(competitive)
    seller = olx_sub.add_parser(
        "competitive-seller",
        help="Crawl a competitor portfolio from a detail-page UI dump (XML file)",
    )
    seller.add_argument("xml", help="Path to the dumped detail-page XML")
    seller.add_argument("--fingerprint", required=True, help="Own ad fingerprint to link against")
    seller.add_argument("--viewed-url", default=None, help="URL of the viewed competitor ad (excluded)")
    seller.add_argument("--viewed-ad-id", default=None, help="Ad-id of the viewed competitor ad (excluded)")
    with_db(seller)

    advisor = olx_sub.add_parser("advisor", help="Portfolio advice + new listings")
    advisor.add_argument("--new", action="store_true", help="Include new-listing suggestions")
    with_db(advisor)

    bootstrap = olx_sub.add_parser("bootstrap", help="Fresh-server setup plan (or run)")
    bootstrap.add_argument("--execute", action="store_true", help="Run commands (default: print)")
    bootstrap.add_argument("--no-emulator", action="store_true")
    bootstrap.add_argument("--no-apt", action="store_true")
    bootstrap.add_argument("--apk", default=None, help="Path to OLX APK to install")

    olx_sub.add_parser("doctor", help="Environment readiness checklist")



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

    if args.olx_command == "detail":
        from aios_core.modules.olx import AdDetailParser
        with open(args.xml, encoding="utf-8") as fh:
            detail = AdDetailParser().parse(fh.read())
        print(json.dumps(detail.to_dict(), ensure_ascii=False, indent=2))
        return True

    if args.olx_command == "chats":
        from aios_core.modules.olx import OLXMessenger
        with OLXStorage(args.db) as storage:
            messenger = OLXMessenger(storage=storage)
            threads = messenger.list_chats()
            print(json.dumps(
                [thread.to_dict() for thread in threads],
                ensure_ascii=False, indent=2,
            ))
        return True

    if args.olx_command == "reply":
        from aios_core.modules.olx import OLXMessenger
        with OLXStorage(args.db) as storage:
            messenger = OLXMessenger(storage=storage)
            result = messenger.send_reply(
                chat_key=args.chat_key,
                text=args.text,
                interlocutor=args.interlocutor,
                auto_send=args.send_now,
            )
            print(json.dumps(result, ensure_ascii=False, indent=2))
        return True

    if args.olx_command == "outbox":
        with OLXStorage(args.db) as storage:
            print(json.dumps(
                storage.outbox_list(status=args.status),
                ensure_ascii=False, indent=2,
            ))
        return True

    if args.olx_command == "own":
        from aios_core.modules.olx import OwnAdsParser, OwnAdsTracker
        with OLXStorage(args.db) as storage:
            tracker = OwnAdsTracker(storage)
            if args.xml:
                with open(args.xml, encoding="utf-8") as fh:
                    ads = OwnAdsParser().parse(fh.read())
                result = tracker.record_snapshot(ads)
                print(json.dumps(result, ensure_ascii=False, indent=2))
            elif args.stagnant:
                items = tracker.stagnant(
                    min_age_days=args.min_age_days,
                    min_views_per_day=args.min_views_per_day,
                )
                print(json.dumps(items, ensure_ascii=False, indent=2))
            else:
                print(json.dumps(
                    storage.own_ads(), ensure_ascii=False, indent=2, default=str
                ))
        return True

    if args.olx_command == "improve":
        from aios_core.modules.olx import AdImprover, OwnAd
        with OLXStorage(args.db) as storage:
            rows = [row for row in storage.own_ads() if row["fingerprint"] == args.fingerprint]
            if not rows:
                print(f"Own ad not found: {args.fingerprint}")
                return True
            row = rows[0]
            own_ad = OwnAd(
                title=row["title"], price=row["price"], currency=row["currency"],
                views=row["last_views"] or 0, url=row["url"], ad_id=row["ad_id"],
                status=row["status"],
            )
            competitors = storage.get_ads(query=args.query)
            print(AdImprover().improve(own_ad, competitors).to_text())
        return True

    if args.olx_command == "repost":
        from aios_core.modules.olx import OwnAd, Reposter
        with OLXStorage(args.db) as storage:
            rows = [row for row in storage.own_ads() if row["fingerprint"] == args.fingerprint]
            if not rows:
                print(f"Own ad not found: {args.fingerprint}")
                return True
            row = rows[0]
            own_ad = OwnAd(
                title=row["title"], price=row["price"], currency=row["currency"],
                url=row["url"], ad_id=row["ad_id"], status=row["status"],
            )
            result = Reposter().repost(own_ad, confirm=args.confirm)
            if result.get("status") == "executed":
                storage.own_ad_set_status(args.fingerprint, "inactive")
            print(json.dumps(result, ensure_ascii=False, indent=2))
        return True

    if args.olx_command == "subscribe":
        from aios_core.modules.olx import SubscriptionManager
        with OLXStorage(args.db) as storage:
            sub_id = SubscriptionManager(storage).add(
                name=args.name or args.query,
                query=args.query,
                min_price=args.min_price,
                max_price=args.max_price,
                city=args.city,
            )
            print(json.dumps({"id": sub_id}, ensure_ascii=False))
        return True

    if args.olx_command == "subscriptions":
        from aios_core.modules.olx import SubscriptionManager
        with OLXStorage(args.db) as storage:
            print(json.dumps(
                SubscriptionManager(storage).list(), ensure_ascii=False, indent=2
            ))
        return True

    if args.olx_command == "favorite":
        from aios_core.modules.olx import FavoritesWatch
        with OLXStorage(args.db) as storage:
            watch = FavoritesWatch(storage)
            if args.remove:
                print(json.dumps({"removed": watch.remove(args.fingerprint)}))
            else:
                print(json.dumps({"added": watch.add(args.fingerprint)}))
        return True

    if args.olx_command == "favorites":
        from aios_core.modules.olx import FavoritesWatch
        with OLXStorage(args.db) as storage:
            watch = FavoritesWatch(storage)
            if args.alerts:
                print(json.dumps(watch.price_alerts(), ensure_ascii=False, indent=2))
            else:
                print(json.dumps(watch.list(), ensure_ascii=False, indent=2))
        return True

    if args.olx_command == "autowatch":
        from aios_core.modules.olx import AutoWatch, WebhookNotifier
        with OLXStorage(args.db) as storage:
            watch = AutoWatch(
                storage=storage,
                collector=OLXCollector(),
                notifier=WebhookNotifier(url=args.webhook, chat_id=args.chat_id),
                max_cards=args.max_cards,
            )
            report = watch.run_cycle(
                queries=args.query or None, collect=not args.no_collect
            )
            print(json.dumps(report, ensure_ascii=False, indent=2, default=str))
        return True

    if args.olx_command == "profile":
        from aios_core.modules.olx import ProfileParser
        with OLXStorage(args.db) as storage:
            if args.xml:
                with open(args.xml, encoding="utf-8") as fh:
                    xml_text = fh.read()
                parser = ProfileParser()
                profile = parser.parse_profile(xml_text)
                for key, value in profile.fields.items():
                    storage.profile_set(key, value)
                payload = profile.to_dict()
                if args.settings:
                    payload["settings"] = parser.settings_from_texts(
                        parser._texts(xml_text)
                    ).to_dict()
                print(json.dumps(payload, ensure_ascii=False, indent=2))
            else:
                print(json.dumps(storage.profile_all(), ensure_ascii=False, indent=2))
        return True

    if args.olx_command == "profile-edit":
        from aios_core.modules.olx import ProfileEditor
        with OLXStorage(args.db) as storage:
            result = ProfileEditor().apply(
                storage, args.field, args.value, confirm=args.confirm
            )
            print(json.dumps(result, ensure_ascii=False, indent=2))
        return True

    if args.olx_command == "competitive-seller":
        from aios_core.modules.olx import CompetitiveWatch, OwnAd
        xml_text = Path(args.xml).read_text(encoding="utf-8")
        with OLXStorage(args.db) as storage:
            rows = [r for r in storage.own_ads() if r["fingerprint"] == args.fingerprint]
            if not rows:
                print(json.dumps({"error": f"own ad '{args.fingerprint}' not found"}))
                return True
            row = rows[0]
            own = OwnAd(
                title=row["title"], price=row["price"], currency=row["currency"],
                views=row["last_views"] or 0, url=row["url"],
                ad_id=row["ad_id"], status=row["status"],
            )
            result = CompetitiveWatch(storage).observe_seller_ads(
                xml_text, own,
                viewed_url=args.viewed_url, viewed_ad_id=args.viewed_ad_id,
            )
            print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
        return True

    if args.olx_command == "competitive":
        from aios_core.modules.olx import CompetitiveWatch, OwnAd
        with OLXStorage(args.db) as storage:
            watch = CompetitiveWatch(storage)
            if args.fingerprint:
                print(json.dumps(
                    watch.report(args.fingerprint), ensure_ascii=False, indent=2, default=str
                ))
            else:
                own_list = [
                    OwnAd(
                        title=row["title"], price=row["price"], currency=row["currency"],
                        views=row["last_views"] or 0, url=row["url"],
                        ad_id=row["ad_id"], status=row["status"],
                    )
                    for row in storage.own_ads(status="active")
                ]
                print(json.dumps(watch.refresh(own_list), ensure_ascii=False, indent=2))
        return True

    if args.olx_command == "advisor":
        from aios_core.modules.olx import StrategyAdvisor
        with OLXStorage(args.db) as storage:
            advisor = StrategyAdvisor(storage)
            payload = {"actions": [a.to_dict() for a in advisor.advise_actions()]}
            if args.new:
                payload["new_listings"] = [
                    n.to_dict() for n in advisor.advise_new_listings()
                ]
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        return True

    if args.olx_command == "bootstrap":
        from aios_core.modules.olx import OLXBootstrap
        import os
        bootstrap = OLXBootstrap(project_root=os.path.dirname(os.path.abspath(__file__)))
        kwargs = {
            "emulator": not args.no_emulator,
            "apt": not args.no_apt,
            "olx_apk": args.apk,
        }
        if args.execute:
            print(json.dumps(bootstrap.execute(**kwargs), ensure_ascii=False, indent=2))
        else:
            print(bootstrap.print_plan(**kwargs))
        return True

    if args.olx_command == "doctor":
        from aios_core.modules.olx import OLXBootstrap
        report = OLXBootstrap().doctor_report()
        print(json.dumps(report, ensure_ascii=False, indent=2))
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
