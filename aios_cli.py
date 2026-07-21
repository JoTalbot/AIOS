#!/usr/bin/env python3
"""
AIOS Command Line Interface v4.1
"""

import argparse
import asyncio
import json
import os
from pathlib import Path
from aios_core import Orchestrator, Database
from aios_core.dashboard import create_dashboard
import uvicorn

DEFAULT_OLX_DB = "olx_ads.sqlite"


def _add_olx_parsers(subparsers) -> None:
    olx_parser = subparsers.add_parser("olx", help="OLX Parser Agent commands")
    olx_sub = olx_parser.add_subparsers(dest="olx_command")

    def with_db(p):
        p.add_argument(
            "--db", default=None,
            help="SQLite database file (переопределяет разрешение профиля)",
        )
        p.add_argument(
            "--profile", default=None,
            help="Имя профиля из реестра (иначе AIOS_PROFILE / default)",
        )

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



def _resolve_olx_profile(args):
    """Профиль OLX для команды: --db пропускает разрешение профиля."""
    from aios_core.platforms import Profile, resolve_profile

    if getattr(args, "db", None):
        return Profile(
            platform="olx", name="cli", db_path=args.db, ephemeral=True,
        )
    return resolve_profile("olx", getattr(args, "profile", None))


def _resolve_olx_db(args) -> str:
    """Путь БД для olx-команды (--db > --profile > AIOS_PROFILE > default)."""
    return _resolve_olx_profile(args).db_path


def _resolve_olx_adb(args):
    """ADB-контроллер, привязанный к устройству профиля (device_serial)."""
    from aios_core.platforms import get_platform

    if getattr(args, "db", None) and not getattr(args, "profile", None):
        # Явный --db без профиля: привязки к устройству нет.
        from aios_core.modules.olx import ADBController

        return ADBController()
    return get_platform("olx").make_adb(
        _resolve_olx_profile(args).device_serial
    )


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
        with OLXStorage(_resolve_olx_db(args)) as storage:
            scheduler = CollectionScheduler(
                collector=OLXCollector(adb=_resolve_olx_adb(args)), storage=storage
            )
            summaries = scheduler.run_once([args.query], max_cards=args.max_cards)
            print(json.dumps(summaries, ensure_ascii=False, indent=2))
        return True

    if args.olx_command == "stats":
        with OLXStorage(_resolve_olx_db(args)) as storage:
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
        with OLXStorage(_resolve_olx_db(args)) as storage:
            ads = storage.get_ads(query=args.query)
            advice = RecommendationEngine().recommend(ads, my_ad=my_ad)
            print(advice.to_text())
        return True

    if args.olx_command == "export":
        with OLXStorage(_resolve_olx_db(args)) as storage:
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
        with OLXStorage(_resolve_olx_db(args)) as storage:
            print(json.dumps(
                storage.price_history(args.fingerprint),
                ensure_ascii=False, indent=2,
            ))
        return True

    if args.olx_command == "drops":
        with OLXStorage(_resolve_olx_db(args)) as storage:
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
        with OLXStorage(_resolve_olx_db(args)) as storage:
            messenger = OLXMessenger(adb=_resolve_olx_adb(args), storage=storage)
            threads = messenger.list_chats()
            print(json.dumps(
                [thread.to_dict() for thread in threads],
                ensure_ascii=False, indent=2,
            ))
        return True

    if args.olx_command == "reply":
        from aios_core.modules.olx import OLXMessenger
        with OLXStorage(_resolve_olx_db(args)) as storage:
            messenger = OLXMessenger(adb=_resolve_olx_adb(args), storage=storage)
            result = messenger.send_reply(
                chat_key=args.chat_key,
                text=args.text,
                interlocutor=args.interlocutor,
                auto_send=args.send_now,
            )
            print(json.dumps(result, ensure_ascii=False, indent=2))
        return True

    if args.olx_command == "outbox":
        with OLXStorage(_resolve_olx_db(args)) as storage:
            print(json.dumps(
                storage.outbox_list(status=args.status),
                ensure_ascii=False, indent=2,
            ))
        return True

    if args.olx_command == "own":
        from aios_core.modules.olx import OwnAdsParser, OwnAdsTracker
        with OLXStorage(_resolve_olx_db(args)) as storage:
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
        with OLXStorage(_resolve_olx_db(args)) as storage:
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
        with OLXStorage(_resolve_olx_db(args)) as storage:
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
        with OLXStorage(_resolve_olx_db(args)) as storage:
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
        with OLXStorage(_resolve_olx_db(args)) as storage:
            print(json.dumps(
                SubscriptionManager(storage).list(), ensure_ascii=False, indent=2
            ))
        return True

    if args.olx_command == "favorite":
        from aios_core.modules.olx import FavoritesWatch
        with OLXStorage(_resolve_olx_db(args)) as storage:
            watch = FavoritesWatch(storage)
            if args.remove:
                print(json.dumps({"removed": watch.remove(args.fingerprint)}))
            else:
                print(json.dumps({"added": watch.add(args.fingerprint)}))
        return True

    if args.olx_command == "favorites":
        from aios_core.modules.olx import FavoritesWatch
        with OLXStorage(_resolve_olx_db(args)) as storage:
            watch = FavoritesWatch(storage)
            if args.alerts:
                print(json.dumps(watch.price_alerts(), ensure_ascii=False, indent=2))
            else:
                print(json.dumps(watch.list(), ensure_ascii=False, indent=2))
        return True

    if args.olx_command == "autowatch":
        from aios_core.modules.olx import AutoWatch, WebhookNotifier
        with OLXStorage(_resolve_olx_db(args)) as storage:
            watch = AutoWatch(
                storage=storage,
                collector=OLXCollector(adb=_resolve_olx_adb(args)),
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
        with OLXStorage(_resolve_olx_db(args)) as storage:
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
        with OLXStorage(_resolve_olx_db(args)) as storage:
            result = ProfileEditor().apply(
                storage, args.field, args.value, confirm=args.confirm
            )
            print(json.dumps(result, ensure_ascii=False, indent=2))
        return True

    if args.olx_command == "competitive-seller":
        from aios_core.modules.olx import CompetitiveWatch, OwnAd
        xml_text = Path(args.xml).read_text(encoding="utf-8")
        with OLXStorage(_resolve_olx_db(args)) as storage:
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
        with OLXStorage(_resolve_olx_db(args)) as storage:
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
        with OLXStorage(_resolve_olx_db(args)) as storage:
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


def _run_platforms(args) -> bool:
    from aios_core.platforms import list_platforms, scaffold_platform

    cmd = getattr(args, "platforms_command", None) or "list"

    if cmd == "from-apk":
        from aios_core.platforms import scaffold_from_apk
        result = scaffold_from_apk(
            args.apk, name=args.name, project_root=args.root,
            locale=args.locale, dry_run=args.dry_run,
        )
        mode = "planned" if args.dry_run else "written"
        print(json.dumps({
            "spec": result["spec"],
            mode: sorted(result["files"]),
        }, ensure_ascii=False, indent=2))
        return True

    if cmd == "fetch-apk":
        from aios_core.platforms import fetch_apk
        try:
            path = fetch_apk(
                args.package, out_dir=args.out, source=args.source,
            )
        except ValueError as exc:
            print(json.dumps({"error": str(exc)}))
            return True
        print(json.dumps({"apk": path, "package": args.package},
                         ensure_ascii=False, indent=2))
        return True

    if cmd == "marker-check":
        from aios_core.platforms import check_platform_markers
        try:
            report = check_platform_markers(
                args.platform, Path(args.dump).read_text(encoding="utf-8"),
            )
        except ValueError as exc:
            print(json.dumps({"error": str(exc)}))
            return True
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return True

    if cmd == "calibrate":
        from aios_core.platforms import (
            CalibrationAdvisor,
            DetailCalibrationAdvisor,
            hints_to_yaml_doc,
            merge_hints,
        )
        from aios_core.platforms.calibrate import write_hints_to_descriptor
        hints = CalibrationAdvisor().analyze(Path(args.dump).read_text(encoding="utf-8"))
        detail_hints = None
        messenger_hints = None
        if args.detail:
            detail_hints = DetailCalibrationAdvisor().analyze_detail(
                Path(args.detail).read_text(encoding="utf-8")
            )
        if args.messages:
            messenger_hints = DetailCalibrationAdvisor().analyze_messenger(
                Path(args.messages).read_text(encoding="utf-8")
            )
        hints = merge_hints(hints, detail_hints, messenger_hints)
        output = {"platform": args.platform, "hints": hints}
        if args.write:
            try:
                output["written"] = write_hints_to_descriptor(
                    args.platform, hints,
                )
            except ValueError as exc:
                print(json.dumps({"error": str(exc)}))
                return True
        else:
            output["yaml_fragment"] = hints_to_yaml_doc(args.platform, hints)
        print(json.dumps(output, ensure_ascii=False, indent=2))
        return True

    if cmd == "codegen":
        from aios_core.platforms.parsergen import write_parser
        import yaml
        yaml_path = Path(args.root) / "platforms" / f"{args.platform}.yaml"
        if not yaml_path.exists():
            print(json.dumps({"error": f"descriptor not found: {yaml_path}"}))
            return True
        doc = yaml.safe_load(yaml_path.read_text(encoding="utf-8")) or {}
        hints = (doc.get("extras") or {}).get("parser_hints") or {}
        try:
            files = write_parser(
                args.platform, hints,
                project_root=args.root,
                android_package=doc.get("android_package") or "",
                dry_run=args.dry_run,
                overwrite=args.force,
            )
        except ValueError as exc:
            print(json.dumps({"error": str(exc)}))
            return True
        mode = "planned" if args.dry_run else "written"
        print(json.dumps(
            {mode: sorted(files)}, ensure_ascii=False, indent=2,
        ))
        return True

    if cmd == "bootup":
        from aios_core.platforms.bootup import bootup_platform
        pool = None
        if args.lease:
            from aios_core.platforms import DevicePool
            pool = DevicePool()  # AIOS_DEVICES_DB / data/devices.sqlite
        try:
            report = bootup_platform(
                apk_path=args.apk,
                name=args.name,
                package=args.package,
                project_root=args.root,
                locale=args.locale,
                dump_path=args.dump,
                query=args.query,
                dry_run=args.dry_run,
                fetch=args.fetch,
                apks_dir=args.apks_dir,
                serial=args.serial,
                pool=pool,
            )
        except ValueError as exc:
            print(json.dumps({"error": str(exc)}))
            return True
        finally:
            if pool is not None:
                pool.close()
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return True

    if cmd == "scaffold":
        files = scaffold_platform(
            args.name, args.package,
            project_root=args.root,
            description=args.description,
            locale=args.locale,
            dry_run=args.dry_run,
        )
        mode = "planned" if args.dry_run else "written"
        print(json.dumps(
            {mode: sorted(files)}, ensure_ascii=False, indent=2,
        ))
        return True

    print(json.dumps(
        [descriptor.to_dict() for descriptor in list_platforms()],
        ensure_ascii=False, indent=2,
    ))
    return True


def _run_instagram(args) -> bool:
    """Instagram agent: doctor / collect / Direct / login-drive."""
    cmd = getattr(args, "instagram_command", None) or "doctor"
    try:
        if cmd == "doctor":
            from aios_core.modules.instagram import InstagramBootstrap
            report = InstagramBootstrap(serial=args.serial).doctor()
            print(json.dumps(report, ensure_ascii=False, indent=2))
            return True

        if cmd == "collect":
            from aios_core.modules.instagram import (
                InstagramCollector,
                InstagramLoginDriver,
                InstagramStorage,
            )
            from aios_core.modules.olx.adb import ADBController
            from aios_core.platforms.pointdrive import PointDrive

            adb = ADBController(package="com.instagram.android",
                                serial=args.serial)
            driver = None
            if args.login:
                login = InstagramLoginDriver(adb=adb, search_drive=PointDrive(adb))
                driver = login.drive
            collector = InstagramCollector(
                adb=adb, driver=driver, directory=args.directory,
            )
            storage = InstagramStorage(args.db)
            try:
                summary = collector.collect_to_storage(
                    storage, query=args.query, max_cards=args.max_cards,
                )
            finally:
                storage.close()
            print(json.dumps(summary, ensure_ascii=False, indent=2))
            return True

        if cmd in ("dm-send", "dm-flush", "dm-outbox"):
            from aios_core.modules.instagram import (
                InstagramMessenger,
                InstagramStorage,
            )
            from aios_core.modules.olx.adb import ADBController

            adb = ADBController(package="com.instagram.android",
                                serial=getattr(args, "serial", None))
            storage = InstagramStorage(args.db)
            try:
                messenger = InstagramMessenger(
                    adb=adb, storage=storage,
                    directory=getattr(args, "directory", "platforms"),
                )
                if cmd == "dm-send":
                    result = messenger.send_reply(
                        args.chat, args.text,
                        interlocutor=args.interlocutor,
                        auto_send=args.auto_send,
                    )
                elif cmd == "dm-flush":
                    result = {"flushed": messenger.flush_outbox()}
                else:
                    result = [
                        {k: item[k] for k in (
                            "id", "chat_key", "interlocutor", "text",
                            "status")}
                        for item in storage.outbox_list(args.status)
                    ]
            finally:
                storage.close()
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return True

        if cmd == "login-drive":
            from aios_core.modules.instagram import (
                InstagramLoginDriver,
                login_screen_detected,
            )
            from aios_core.modules.olx.adb import ADBController
            from aios_core.platforms import parser_for
            from aios_core.platforms.pointdrive import PointDrive

            adb = ADBController(package="com.instagram.android",
                                serial=args.serial)
            driver = InstagramLoginDriver(adb=adb, search_drive=PointDrive(adb))
            xml = driver.drive("com.instagram.android", args.query)
            output: dict = {
                "status": "ok",
                "dump_bytes": len(xml.encode("utf-8")),
                "login_wall": login_screen_detected(xml),
            }
            try:
                cards = parser_for(
                    "instagram", directory=args.directory,
                ).parse(xml, query=args.query)
                output["cards"] = [
                    {"title": c.title, "price": c.price,
                     "currency": c.currency} for c in cards
                ]
            except ValueError:
                output["cards"] = "parser hints not calibrated"
            print(json.dumps(output, ensure_ascii=False, indent=2))
            return True

    except ValueError as exc:
        print(json.dumps({"error": str(exc)}))
        return True

    return False


def _run_profiles(args) -> bool:
    from aios_core.platforms import Profile, ProfileStore

    store = ProfileStore.default()
    cmd = args.profiles_command

    if cmd == "list":
        print(json.dumps(
            [p.to_dict() for p in store.list(args.platform)],
            ensure_ascii=False, indent=2,
        ))
        return True

    if cmd == "add":
        try:
            profile = store.add(Profile(
                platform=args.platform, name=args.name,
                device_serial=args.device, android_user=args.android_user,
                db_path=args.db, locale=args.locale, notes=args.notes,
                is_default=args.default,
            ))
        except ValueError as exc:
            print(json.dumps({"error": str(exc)}, ensure_ascii=False))
            return True
        print(json.dumps(profile.to_dict(), ensure_ascii=False, indent=2))
        return True

    if cmd == "show":
        profile = store.get(args.platform, args.name)
        if profile is None:
            print(json.dumps(
                {"error": f"profile '{args.platform}:{args.name}' not found"},
                ensure_ascii=False,
            ))
            return True
        print(json.dumps(profile.to_dict(), ensure_ascii=False, indent=2))
        return True

    if cmd == "remove":
        removed = store.remove(args.platform, args.name)
        print(json.dumps({"removed": removed}))
        return True

    if cmd == "set-default":
        profile = store.set_default(args.platform, args.name)
        if profile is None:
            print(json.dumps(
                {"error": f"profile '{args.platform}:{args.name}' not found"},
                ensure_ascii=False,
            ))
            return True
        print(json.dumps(profile.to_dict(), ensure_ascii=False, indent=2))
        return True

    return False


def _run_devices(args) -> bool:
    from aios_core.platforms import DevicePool

    with DevicePool() as pool:
        cmd = args.devices_command

        if cmd == "register":
            record = pool.register(args.serial, avd_name=args.avd)
            print(json.dumps(record, ensure_ascii=False, indent=2))
            return True

        if cmd == "list":
            print(json.dumps(pool.status(), ensure_ascii=False, indent=2))
            return True

        if cmd == "lease":
            from aios_core.platforms import ProfileStore
            store = ProfileStore.default() if args.sync else None
            record = pool.lease(
                args.profile, serial=args.serial, profile_store=store
            )
            if record is None:
                if args.enqueue:
                    wait_id = pool.enqueue(args.profile, priority=args.priority)
                    print(json.dumps({"queued": wait_id, "profile": args.profile}))
                    return True
                print(json.dumps(
                    {"error": "no idle device available"}, ensure_ascii=False
                ))
                return True
            print(json.dumps(record, ensure_ascii=False, indent=2))
            return True

        if cmd == "waitlist":
            print(json.dumps(pool.waitlist(), ensure_ascii=False, indent=2))
            return True

        if cmd == "enqueue":
            wait_id = pool.enqueue(args.profile, priority=args.priority)
            print(json.dumps({"queued": wait_id, "profile": args.profile}))
            return True

        if cmd == "cancel-wait":
            cancelled = pool.cancel_wait(args.profile)
            print(json.dumps({"cancelled": cancelled}))
            return True

        if cmd == "release":
            freed = pool.release(args.profile)
            print(json.dumps({"released": freed}))
            return True

        if cmd == "heartbeat":
            ok = pool.heartbeat(args.serial)
            print(json.dumps({"ok": ok}))
            return True

        if cmd == "reap":
            stale = pool.reap_stale(args.max_silence_s)
            print(json.dumps({"reaped": stale}))
            return True

        if cmd == "limits":
            if args.set_limit:
                key, sep, raw = args.set_limit.partition("=")
                if not sep:
                    raise ValueError("--set expects KEY=VALUE")
                pool.set_limit(key.strip(), int(raw))
            print(json.dumps(pool.limits(), ensure_ascii=False, indent=2))
            return True

        if cmd == "ensure":
            from aios_core.platforms import ProfileStore, ensure_device
            record = ensure_device(
                args.profile, pool=pool,
                profile_store=ProfileStore.default(),
                avd_prefix=args.avd_prefix,
            )
            if record is None:
                print(json.dumps(
                    {"error": "could not lease or create a device"},
                    ensure_ascii=False,
                ))
                return True
            print(json.dumps(record, ensure_ascii=False, indent=2))
            return True

    if cmd == "monitor":
        from aios_core.platforms import PoolMonitor
        monitor = PoolMonitor(reap_after_s=args.reap_after_s)
        if args.once:
            print(json.dumps(monitor.run_once()))
            monitor.close()
            return True
        monitor.start(interval_s=args.interval)
        print(json.dumps({"monitoring": True, "interval_s": args.interval}))
        try:
            import time as _time
            while True:
                _time.sleep(1)
        except KeyboardInterrupt:
            monitor.close()
        return True

    return False


def _run_shards(args) -> bool:
    from aios_core.platforms import ShardRouter

    with ShardRouter() as router:
        cmd = args.shards_command

        if cmd == "list":
            print(json.dumps(router.hosts(), ensure_ascii=False, indent=2))
            return True

        if cmd == "add":
            record = router.add_host(args.host, args.base_url)
            print(json.dumps(record, ensure_ascii=False, indent=2))
            return True

        if cmd == "remove":
            removed = router.remove_host(args.host)
            print(json.dumps({"removed": removed}))
            return True

        if cmd == "route":
            route = router.route_for(args.profile)
            if route is None:
                print(json.dumps({"error": "no healthy shard hosts"}))
                return True
            print(json.dumps(route, ensure_ascii=False, indent=2))
            return True

        if cmd == "unroute":
            removed = router.unroute(args.profile)
            print(json.dumps({"unrouted": removed}))
            return True

    if cmd == "monitor":
        from aios_core.platforms import ShardHealthMonitor
        monitor = ShardHealthMonitor()
        if args.once:
            print(json.dumps(monitor.run_once(), ensure_ascii=False))
            monitor.close()
            return True
        monitor.start(interval_s=args.interval)
        print(json.dumps({"monitoring": True, "interval_s": args.interval}))
        try:
            import time as _time
            while True:
                _time.sleep(1)
        except KeyboardInterrupt:
            monitor.close()
        return True

    return False


def _run_cron_plan(args) -> bool:
    """Генерирует crontab: per-profile AutoWatch + монитор пула."""
    from aios_core.platforms import ProfileStore

    store = ProfileStore.default()
    profiles = store.list(args.platform or None)
    root = os.path.dirname(os.path.abspath(__file__))
    interval = args.interval
    lines = [
        "# AIOS cron plan — сгенерировано 'aios cron-plan'",
        f"# платформа: {args.platform or 'все'} · профилей: {len(profiles)}",
        "SHELL=/bin/bash",
        f"AIOS_PROFILES_DB={os.environ.get('AIOS_PROFILES_DB', f'{root}/data/profiles.sqlite')}",
        f"AIOS_DEVICES_DB={os.environ.get('AIOS_DEVICES_DB', f'{root}/data/devices.sqlite')}",
        "",
    ]
    webhook = f" --webhook {args.webhook}" if args.webhook else ""
    for profile in profiles:
        lines.append(
            f"*/{interval} * * * * cd {root} && "
            f"python3 aios_cli.py olx autowatch --profile {profile.name}{webhook} "
            f">> {root}/data/autowatch-{profile.key.replace(':', '_')}.log 2>&1"
        )
    lines.append(
        f"*/{interval} * * * * cd {root} && "
        f"python3 aios_cli.py devices monitor --once "
        f">> {root}/data/pool-monitor.log 2>&1"
    )
    if args.with_marker_check:
        from aios_core.platforms import load_catalog
        platforms = [d.name for d in load_catalog()] or ["olx"]
        lines.append("")
        lines.append(
            "# Marker drift guard: раскомментируйте и укажите продюсера "
            "свежего дампа выдачи (data/marker-<platform>.xml)"
        )
        for platform in platforms:
            lines.append(
                f"# 0 */6 * * * cd {root} && "
                f"python3 aios_cli.py platforms marker-check "
                f"--platform {platform} "
                f"--dump {root}/data/marker-{platform}.xml "
                f">> {root}/data/marker-{platform}.log 2>&1"
            )
    plan = "\n".join(lines)
    if args.write:
        Path(args.write).parent.mkdir(parents=True, exist_ok=True)
        Path(args.write).write_text(plan + "\n", encoding="utf-8")
        print(json.dumps({"written": args.write, "profiles": len(profiles)}))
    else:
        print(plan)
    return True


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

    # Marketplace platforms registry
    platforms_parser = subparsers.add_parser(
        "platforms", help="List/scaffold registered marketplace platforms"
    )
    plat_sub = platforms_parser.add_subparsers(dest="platforms_command")
    plat_sub.add_parser("list", help="List registered platforms")

    p_scaf = plat_sub.add_parser(
        "scaffold", help="Generate a new platform skeleton from a descriptor"
    )
    p_scaf.add_argument("--name", required=True, help="e.g. prom-ua")
    p_scaf.add_argument("--package", required=True, help="Android package, e.g. ua.prom.app")
    p_scaf.add_argument("--description", default="")
    p_scaf.add_argument("--locale", default="uk-UA")
    p_scaf.add_argument("--root", default=".", help="Project root")
    p_scaf.add_argument("--dry-run", action="store_true")

    p_apk = plat_sub.add_parser(
        "from-apk", help="Auto-scaffold a platform from an APK (aapt badging)"
    )
    p_apk.add_argument("apk", help="Path to the .apk file")
    p_apk.add_argument("--name", default=None,
                       help="Platform name (default: last package segment)")
    p_apk.add_argument("--locale", default="uk-UA")
    p_apk.add_argument("--root", default=".", help="Project root")
    p_apk.add_argument("--dry-run", action="store_true")

    p_cal = plat_sub.add_parser(
        "calibrate", help="Extract parser hints from a search-screen UI dump"
    )
    p_cal.add_argument("--platform", required=True, help="Platform name")
    p_cal.add_argument("--dump", required=True, help="Path to uiautomator XML dump")
    p_cal.add_argument("--detail", default=None,
                       help="Detail-screen UI dump (seller/CTA/description)")
    p_cal.add_argument("--messages", default=None,
                       help="Messenger-screen UI dump (input/send/bubbles)")
    p_cal.add_argument("--write", action="store_true",
                       help="Write hints into platforms/<name>.yaml extras")

    p_fetch = plat_sub.add_parser(
        "fetch-apk", help="Download a platform APK via apkeep"
    )
    p_fetch.add_argument("package", help="Android package, e.g. com.instagram.android")
    p_fetch.add_argument("--out", default="apks", help="Download directory")
    p_fetch.add_argument("--source", default="apkpure",
                         help="apkeep source: apkpure/google-play/f-droid")

    p_mark = plat_sub.add_parser(
        "marker-check",
        help="Diff descriptor parser_hints markers against a fresh dump",
    )
    p_mark.add_argument("--platform", required=True, help="Platform name")
    p_mark.add_argument("--dump", required=True,
                        help="Fresh search-screen UI dump")

    p_gen = plat_sub.add_parser(
        "codegen", help="Compile card_parser.py from descriptor parser_hints"
    )
    p_gen.add_argument("--platform", required=True, help="Platform name")
    p_gen.add_argument("--root", default=".", help="Project root")
    p_gen.add_argument("--dry-run", action="store_true")
    p_gen.add_argument("--force", action="store_true",
                       help="Overwrite an already generated card_parser.py")

    p_boot = plat_sub.add_parser(
        "bootup",
        help="E2E pipeline: APK dump → scaffold → calibrate → codegen → verify",
    )
    p_boot.add_argument("--apk", default=None,
                        help="Path to the .apk, or package name with --fetch")
    p_boot.add_argument("--name", default=None,
                        help="Platform name (with --package, skips APK)")
    p_boot.add_argument("--package", default=None,
                        help="Android package (with --name, skips APK)")
    p_boot.add_argument("--dump", default=None,
                        help="Search-screen UI dump for calibration")
    p_boot.add_argument("--query", default=None,
                        help="Search query for the live calibration drive")
    p_boot.add_argument("--fetch", action="store_true",
                        help="Download the APK via apkeep when missing")
    p_boot.add_argument("--apks-dir", default="apks",
                        help="Directory for downloaded APKs")
    p_boot.add_argument("--serial", default=None,
                        help="ADB serial for the live calibration drive")
    p_boot.add_argument("--lease", action="store_true",
                        help="Lease a device for the drive from DevicePool")
    p_boot.add_argument("--locale", default="uk-UA")
    p_boot.add_argument("--root", default=".", help="Project root")
    p_boot.add_argument("--dry-run", action="store_true")

    # Instagram platform agent (полный функционал)
    ig_parser = subparsers.add_parser(
        "instagram", help="Instagram agent: doctor/collect/Direct/login-drive"
    )
    ig_sub = ig_parser.add_subparsers(dest="instagram_command")

    ig_sub.add_parser("doctor", help="Readiness checks (adb/secrets/hints/device)"
                      ).add_argument(
        "--serial", default=None, help="ADB serial to verify online")

    ig_col = ig_sub.add_parser(
        "collect", help="Collect feed/search cards into InstagramStorage")
    ig_col.add_argument("--db", default="data/instagram.sqlite")
    ig_col.add_argument("--query", default=None)
    ig_col.add_argument("--max", type=int, default=100, dest="max_cards")
    ig_col.add_argument("--serial", default=None, help="ADB serial")
    ig_col.add_argument("--login", action="store_true",
                        help="Pre-drive with the login wall driver")
    ig_col.add_argument("--directory", default="platforms")

    ig_dm = ig_sub.add_parser(
        "dm-send", help="Guarded Direct reply (outbox by default)")
    ig_dm.add_argument("--chat", required=True, help="Chat key")
    ig_dm.add_argument("--text", required=True)
    ig_dm.add_argument("--interlocutor", default=None)
    ig_dm.add_argument("--db", default="data/instagram.sqlite")
    ig_dm.add_argument("--serial", default=None)
    ig_dm.add_argument("--directory", default="platforms")
    ig_dm.add_argument("--auto-send", action="store_true",
                       help="Send immediately instead of queueing")

    ig_out = ig_sub.add_parser(
        "dm-flush", help="Send every approved outbox entry")
    ig_out.add_argument("--db", default="data/instagram.sqlite")
    ig_out.add_argument("--serial", default=None)
    ig_out.add_argument("--directory", default="platforms")

    ig_outbox = ig_sub.add_parser("dm-outbox", help="List Direct outbox entries")
    ig_outbox.add_argument("--db", default="data/instagram.sqlite")
    ig_outbox.add_argument("--status", default=None)

    ig_drv = ig_sub.add_parser(
        "login-drive", help="Open Instagram past the login wall, dump screen")
    ig_drv.add_argument("--query", default=None,
                        help="Search query via PointDrive after login")
    ig_drv.add_argument("--serial", default=None)
    ig_drv.add_argument("--directory", default="platforms")

    # Platform profiles (accounts)
    profiles_parser = subparsers.add_parser(
        "profiles", help="Manage platform profiles (accounts)"
    )
    prof_sub = profiles_parser.add_subparsers(dest="profiles_command")

    p_list = prof_sub.add_parser("list", help="List profiles")
    p_list.add_argument("--platform", default=None)

    p_add = prof_sub.add_parser("add", help="Register a profile")
    p_add.add_argument("--platform", required=True)
    p_add.add_argument("--name", required=True)
    p_add.add_argument("--device", default=None, help="ADB serial (device binding)")
    p_add.add_argument("--db", default=None, help="Custom SQLite path")
    p_add.add_argument("--android-user", type=int, default=0)
    p_add.add_argument("--locale", default="uk-UA")
    p_add.add_argument("--notes", default="")
    p_add.add_argument("--default", action="store_true", help="Make platform default")

    for p_cmd in ("show", "remove", "set-default"):
        p_one = prof_sub.add_parser(p_cmd, help=f"{p_cmd} profile")
        p_one.add_argument("--platform", required=True)
        p_one.add_argument("--name", required=True)

    # Shard routing across hosts
    shards_parser = subparsers.add_parser(
        "shards", help="Shard routing: hosts and sticky profile routes"
    )
    sh_sub = shards_parser.add_subparsers(dest="shards_command")
    sh_sub.add_parser("list", help="List shard hosts")

    sh_add = sh_sub.add_parser("add", help="Register a shard host")
    sh_add.add_argument("--host", required=True)
    sh_add.add_argument("--base-url", required=True)

    sh_rm = sh_sub.add_parser("remove", help="Remove a shard host")
    sh_rm.add_argument("--host", required=True)

    for sub_name in ("route", "unroute"):
        sh_route = sh_sub.add_parser(sub_name, help=f"{sub_name} a profile")
        sh_route.add_argument("--profile", required=True)

    sh_mon = sh_sub.add_parser("monitor", help="ShardHealthMonitor: host probes")
    sh_mon.add_argument("--interval", type=float, default=30.0)
    sh_mon.add_argument("--once", action="store_true", help="single cycle (cron)")

    # Crontab generator for per-profile automation
    cron_parser = subparsers.add_parser(
        "cron-plan", help="Generate crontab: per-profile AutoWatch + pool monitor"
    )
    cron_parser.add_argument("--platform", default="olx")
    cron_parser.add_argument("--interval", type=int, default=15,
                             help="minutes between runs")
    cron_parser.add_argument("--webhook", default=None, help="webhook URL for alerts")
    cron_parser.add_argument("--write", default=None, help="write to file instead of stdout")
    cron_parser.add_argument("--with-marker-check", action="store_true",
                             help="add commented marker-check lines per catalog platform")

    # Device pool (emulators/physical devices leased to profiles)
    devices_parser = subparsers.add_parser(
        "devices", help="Device pool: register/lease/release emulators"
    )
    dev_sub = devices_parser.add_subparsers(dest="devices_command")

    dev_sub.add_parser("list", help="Pool status")

    d_reg = dev_sub.add_parser("register", help="Register a device")
    d_reg.add_argument("--serial", required=True)
    d_reg.add_argument("--avd", default=None, help="AVD name")

    d_lease = dev_sub.add_parser("lease", help="Lease a device to a profile")
    d_lease.add_argument("--profile", required=True, help="profile key, e.g. olx:work")
    d_lease.add_argument("--serial", default=None, help="pin a specific device")
    d_lease.add_argument("--enqueue", action="store_true",
                         help="put on the waitlist when no idle device")
    d_lease.add_argument("--priority", type=int, default=0)
    d_lease.add_argument("--sync", action="store_true",
                         help="also write device_serial into the profiles registry")

    dev_sub.add_parser("waitlist", help="Show the lease waitlist")

    d_enq = dev_sub.add_parser("enqueue", help="Put a profile on the waitlist")
    d_enq.add_argument("--profile", required=True)
    d_enq.add_argument("--priority", type=int, default=0)

    d_cw = dev_sub.add_parser("cancel-wait", help="Remove a profile from the waitlist")
    d_cw.add_argument("--profile", required=True)

    d_rel = dev_sub.add_parser("release", help="Release a profile's device")
    d_rel.add_argument("--profile", required=True)

    d_hb = dev_sub.add_parser("heartbeat", help="Device heartbeat")
    d_hb.add_argument("--serial", required=True)

    d_reap = dev_sub.add_parser("reap", help="Mark silent devices offline")
    d_reap.add_argument("--max-silence-s", type=float, default=900.0)

    d_ensure = dev_sub.add_parser(
        "ensure", help="Guarantee a device for a profile (lease or create AVD)"
    )
    d_ensure.add_argument("--profile", required=True)
    d_ensure.add_argument("--avd-prefix", default="aios")

    d_mon = dev_sub.add_parser("monitor", help="PoolMonitor: adb heartbeats")
    d_mon.add_argument("--interval", type=float, default=30.0)
    d_mon.add_argument("--once", action="store_true", help="single cycle (cron)")
    d_mon.add_argument("--reap-after-s", type=float, default=900.0)

    d_lim = dev_sub.add_parser("limits", help="Show/set pool quotas")
    d_lim.add_argument("--set", dest="set_limit", default=None,
                       metavar="KEY=VALUE", help="e.g. max_busy:olx=4")

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
    elif args.command == "platforms":
        if not _run_platforms(args):
            parser.parse_args(["platforms", "--help"])
    elif args.command == "instagram":
        if not _run_instagram(args):
            parser.parse_args(["instagram", "--help"])
    elif args.command == "profiles":
        if not _run_profiles(args):
            parser.parse_args(["profiles", "--help"])
    elif args.command == "shards":
        if not _run_shards(args):
            parser.parse_args(["shards", "--help"])
    elif args.command == "cron-plan":
        if not _run_cron_plan(args):
            parser.parse_args(["cron-plan", "--help"])
    elif args.command == "devices":
        try:
            handled = _run_devices(args)
        except ValueError as exc:
            print(json.dumps({"error": str(exc)}, ensure_ascii=False))
            handled = True
        if not handled:
            parser.parse_args(["devices", "--help"])
    elif args.command == "olx":
        try:
            handled = _run_olx(args)
        except ValueError as exc:
            # Например: профиль не найден в реестре.
            print(json.dumps({"error": str(exc)}, ensure_ascii=False))
            handled = True
        if not handled:
            parser.parse_args(["olx", "--help"])
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
