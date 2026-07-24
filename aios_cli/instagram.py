"""AIOS CLI — Instagram agent commands."""

import json
from pathlib import Path

_import_cache: dict = {}


def _lazy_import(module_path: str, attr: str | None = None):
    """Import module on first use and cache result."""
    key = (module_path, attr)
    if key not in _import_cache:
        import importlib
        mod = importlib.import_module(module_path)
        _import_cache[key] = getattr(mod, attr) if attr else mod
    return _import_cache[key]

DEFAULT_OLX_DB = "olx_ads.sqlite"


def _run_instagram(args) -> bool:
    """Instagram agent: doctor / collect / Direct / login-drive."""
    cmd = getattr(args, "instagram_command", None) or "doctor"
    try:
        if cmd == "doctor":
            from aios_core.modules.instagram import InstagramBootstrap

            report = InstagramBootstrap(serial=args.serial).doctor()
            print(json.dumps(report, ensure_ascii=False, indent=2))
            return True

        if cmd == "reels":
            from aios_core.modules.instagram import InstagramStorage
            from aios_core.modules.olx.adb import ADBController
            from aios_core.modules.olx.notifier import WebhookNotifier
            from aios_core.platforms import get_platform, reels_driver_for
            from aios_core.platforms.reelscout import ReelsCollector

            adb = ADBController(package="com.instagram.android", serial=args.serial)
            driver = None
            if args.open_tab:
                driver = reels_driver_for(
                    "instagram",
                    adb=adb,
                    directory=args.directory,
                ).drive
            notifier = WebhookNotifier(url=args.webhook) if args.webhook else None
            collector = ReelsCollector(
                get_platform("instagram"),
                adb=adb,
                directory=args.directory,
                driver=driver,
                notifier=notifier,
            )
            storage = InstagramStorage(args.db)
            try:
                written, cards = collector.collect_to_storage(
                    storage,
                    max_cards=args.max,
                )
            finally:
                storage.close()
            print(
                json.dumps(
                    {
                        "new": written,
                        "seen": len(cards),
                        "open_tab": bool(args.open_tab),
                        "notified": bool(notifier and written),
                        "cards": [c.to_dict() for c in cards],
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )
            return True

        if cmd == "autopilot":
            from aios_core.modules.instagram import (
                InstagramCollector,
                InstagramLoginDriver,
                InstagramMessenger,
                InstagramStorage,
                PostComposer,
            )
            from aios_core.modules.olx.adb import ADBController
            from aios_core.modules.olx.notifier import WebhookNotifier
            from aios_core.platforms import get_platform, reels_driver_for
            from aios_core.platforms.pointdrive import PointDrive
            from aios_core.platforms.reelscout import ReelsCollector

            adb = ADBController(package="com.instagram.android", serial=args.serial)
            driver = None
            if args.login:
                login = InstagramLoginDriver(adb=adb, search_drive=PointDrive(adb))
                driver = login.drive
            pacer = None
            if getattr(args, "pace_actions", 0):
                from aios_core.platforms.pacing import Pacer

                pacer = Pacer(
                    actions_per_hour=getattr(args, "pace_actions", None),
                    jitter_s=(0.4, getattr(args, "pace_jitter", None)),
                )
            storage = InstagramStorage(args.db)
            steps: dict = {}
            try:
                cards_collector = InstagramCollector(
                    adb=adb,
                    driver=driver,
                    directory=args.directory,
                    pacer=pacer,
                )
                steps["collect"] = cards_collector.collect_to_storage(
                    storage,
                    query=args.query,
                    max_cards=args.max,
                )
                notifier = WebhookNotifier(url=args.webhook) if args.webhook else None
                tab_driver = None
                if args.open_tab:
                    tab_driver = reels_driver_for(
                        "instagram",
                        adb=adb,
                        directory=args.directory,
                    ).drive
                reels = ReelsCollector(
                    get_platform("instagram"),
                    adb=adb,
                    directory=args.directory,
                    driver=tab_driver,
                    notifier=notifier,
                    pacer=pacer,
                )
                written_reels, reels_cards = reels.collect_to_storage(
                    storage,
                    max_cards=args.reels_max,
                )
                steps["reels"] = {
                    "new": written_reels,
                    "seen": len(reels_cards),
                    "open_tab": bool(args.open_tab),
                    "notified": bool(notifier and written_reels),
                    "cards": [c.to_dict() for c in reels_cards],
                }
                messenger = InstagramMessenger(
                    adb=adb,
                    storage=storage,
                    directory=args.directory,
                )
                steps["dm_flush"] = [
                    {"id": r["id"], "status": r["status"]} for r in messenger.flush_outbox()
                ]
            finally:
                storage.close()
            if args.own:
                from aios_core.modules.instagram import OwnPostsParser
                from aios_core.modules.olx.own_ads import OwnAdsTracker

                if args.own_dump:
                    own_xml = Path(args.own_dump).read_text(encoding="utf-8")
                else:
                    target = "data/instagram_own.xml"
                    adb.dump_ui(target)
                    if not Path(target).exists():
                        raise RuntimeError(
                            "own-posts: dump_ui не вернул экран профиля — "
                            "передайте --own-dump grid.xml"
                        )
                    own_xml = Path(target).read_text(encoding="utf-8")
                posts = OwnPostsParser(markers=None).parse(own_xml)
                storage = InstagramStorage(args.db)
                try:
                    own_report = OwnAdsTracker(storage).record_snapshot(
                        [post.to_own_ad() for post in posts],
                    )
                finally:
                    storage.close()
                own_notifier = WebhookNotifier(url=args.webhook) if args.webhook else None
                deltas = own_report.get("deltas") or {}
                negative = {
                    fp: d
                    for fp, d in deltas.items()
                    if (d.get("views_delta") or 0) < 0 or (d.get("favorites_delta") or 0) < 0
                }
                if own_notifier is not None and (own_report.get("new") or negative):
                    own_notifier.send(
                        "own-posts",
                        {
                            "platform": "instagram",
                            "recorded": own_report.get("recorded", 0),
                            "new": own_report.get("new", 0),
                            "negative_counters": [d.get("title") for d in negative.values()],
                        },
                    )
                steps["own"] = {
                    **own_report,
                    "posts": [post.to_dict() for post in posts],
                    "notified": bool(own_notifier and (own_report.get("new") or negative)),
                }
            if args.promote:
                from aios_core.modules.olx.own_ads import OwnAdsTracker
                from aios_core.platforms.promote import promotion_plan

                storage = InstagramStorage(args.db)
                try:
                    stagnant = OwnAdsTracker(
                        storage,
                    ).stagnant(
                        min_age_days=int(getattr(args, "promote_min_age_days", 7) or 7),
                    )
                finally:
                    storage.close()
                plan = promotion_plan(
                    stagnant,
                    daily_budget=float(getattr(args, "promote_budget", 0) or 0),
                )
                promote_notifier = WebhookNotifier(url=args.webhook) if args.webhook else None
                if promote_notifier is not None and plan["candidates"]:
                    promote_notifier.send(
                        "promote-suggestion",
                        {
                            "platform": "instagram",
                            "candidates": [c["title"] for c in plan["candidates"]],
                            "budget": plan["budget"],
                            "note": "DRY-RUN план в steps.promote",
                        },
                    )
                steps["promote"] = {
                    **plan,
                    "notified": bool(promote_notifier and plan["candidates"]),
                }
            if args.post_image:
                steps["post"] = PostComposer(adb=adb).publish(
                    args.post_image,
                    args.post_text,
                    confirm=args.confirm,
                )
            report = {
                "query": args.query,
                "login_drive": args.login,
                "steps": steps,
            }
            if pacer is not None:
                report["pacing"] = pacer.stats()
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

            adb = ADBController(package="com.instagram.android", serial=args.serial)
            driver = None
            if args.login:
                login = InstagramLoginDriver(adb=adb, search_drive=PointDrive(adb))
                driver = login.drive
            collector = InstagramCollector(
                adb=adb,
                driver=driver,
                directory=args.directory,
            )
            storage = InstagramStorage(args.db)
            try:
                summary = collector.collect_to_storage(
                    storage,
                    query=args.query,
                    max_cards=args.max,
                )
            finally:
                storage.close()
            print(json.dumps(summary, ensure_ascii=False, indent=2))
            return True

        if cmd in ("dm-send", "dm-flush", "dm-outbox"):
            from aios_core.modules.instagram import InstagramMessenger, InstagramStorage
            from aios_core.modules.olx.adb import ADBController

            adb = ADBController(
                package="com.instagram.android", serial=getattr(args, "serial", None)
            )
            storage = InstagramStorage(args.db)
            try:
                messenger = InstagramMessenger(
                    adb=adb,
                    storage=storage,
                    directory=getattr(args, "directory", "platforms"),
                )
                if cmd == "dm-send":
                    result = messenger.send_reply(
                        args.chat,
                        args.text,
                        interlocutor=getattr(args, "interlocutor", None),
                        auto_send=args.auto_send,
                    )
                elif cmd == "dm-flush":
                    result = {"flushed": messenger.flush_outbox()}
                else:
                    result = [
                        {k: item[k] for k in ("id", "chat_key", "interlocutor", "text", "status")}
                        for item in storage.outbox_list(getattr(args, "status", None))
                    ]
            finally:
                storage.close()
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return True

        if cmd == "own":
            from aios_core.modules.instagram import InstagramStorage, OwnPostsParser
            from aios_core.modules.olx.adb import ADBController
            from aios_core.modules.olx.own_ads import OwnAdsTracker

            if args.dump:
                xml = Path(args.dump).read_text(encoding="utf-8")
            else:
                adb = ADBController(package="com.instagram.android", serial=args.serial)
                target = "data/instagram_own.xml"
                pulled = adb.dump_ui(target)
                if not Path(target).exists():
                    raise ValueError(
                        "dump_ui failed (no device?) — pass --dump "
                        f"({(pulled.get('stderr') or '')[:120]})"
                    )
                xml = Path(target).read_text(encoding="utf-8")
            markers = getattr(args, "marker", None) or None
            posts = OwnPostsParser(markers=markers).parse(xml)
            storage = InstagramStorage(args.db)
            try:
                report = OwnAdsTracker(storage).record_snapshot(
                    [post.to_own_ad() for post in posts],
                )
            finally:
                storage.close()
            report["posts"] = [post.to_dict() for post in posts]
            print(json.dumps(report, ensure_ascii=False, indent=2))
            return True

        if cmd == "post":
            from aios_core.modules.instagram import PostComposer
            from aios_core.modules.olx.adb import ADBController

            adb = ADBController(package="com.instagram.android", serial=args.serial)
            result = PostComposer(adb=adb).publish(
                args.image,
                args.text,
                confirm=args.confirm,
            )
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

            adb = ADBController(package="com.instagram.android", serial=args.serial)
            driver = InstagramLoginDriver(adb=adb, search_drive=PointDrive(adb))
            xml = driver.drive("com.instagram.android", args.query)
            output: dict = {
                "status": "ok",
                "dump_bytes": len(xml.encode("utf-8")),
                "login_wall": login_screen_detected(xml),
            }
            try:
                cards = parser_for(
                    "instagram",
                    directory=args.directory,
                ).parse(xml, query=args.query)
                output["cards"] = [
                    {"title": c.title, "price": c.price, "currency": c.currency} for c in cards
                ]
            except ValueError:
                output["cards"] = "parser hints not calibrated"
            print(json.dumps(output, ensure_ascii=False, indent=2))
            return True

    except (ValueError, RuntimeError) as exc:
        print(json.dumps({"error": str(exc)}))
        return True

    return False


def _adb_dump_driver(default_serial=None):
    """Build a driver callable for remote UI dump (bootup/onboard).

    Returns a function ``driver(package, query=None, serial=None)`` that opens
    the app (optionally executes a PointDrive search) and returns the UI XML
    dump as a string.
    """
    import time

    def driver(package, query=None, serial=None):
        import tempfile

        from aios_core.modules.olx.adb import ADBController
        from aios_core.platforms.pointdrive import PointDrive

        adb = ADBController(package=package, serial=serial or default_serial)
        if query:
            return PointDrive(adb).drive(package, query)
        adb.open_app()
        time.sleep(2.0)
        with tempfile.NamedTemporaryFile(suffix=".xml", delete=False) as tmp:
            adb.dump_ui(tmp.name)
            return Path(tmp.name).read_text(encoding="utf-8")

    return driver

