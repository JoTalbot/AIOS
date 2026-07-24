#!/usr/bin/env python3
"""AIOS CLI — platforms, profiles, devices, shards, cron-plan."""

import json
import os
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


def _run_platforms(args) -> bool:
    """Dispatch a ``platforms`` subcommand: list, scaffold, from-apk, autowatch,
    fetch-apk, marker-check, calibrate, codegen, bootup, reels, or doctor.

    Returns True when the command was recognized and executed.
    """
    from aios_core.platforms import list_platforms, scaffold_platform

    cmd = getattr(args, "platforms_command", None) or "list"

    if cmd == "from-apk":
        from aios_core.platforms import scaffold_from_apk

        result = scaffold_from_apk(
            args.apk,
            name=args.name,
            project_root=args.root,
            locale=args.locale,
            dry_run=args.dry_run,
        )
        mode = "planned" if args.dry_run else "written"
        print(
            json.dumps(
                {
                    "spec": result["spec"],
                    mode: sorted(result["files"]),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return True

    if cmd == "autowatch":
        from aios_core.platforms.autowatch import autowatch_cycle

        driver = None
        if args.drive != "none":
            from aios_core.platforms import get_platform
            from aios_core.platforms.pointdrive import PointDrive
            from aios_core.platforms.resolver import adb_for

            descriptor = get_platform(args.platform)
            adb = adb_for(args.platform, args.profile or None)
            login_driver = None
            if args.drive == "login":
                import importlib

                try:
                    login_mod = importlib.import_module(f"{descriptor.agent_module}.login")
                    for attr in dir(login_mod):
                        candidate = getattr(login_mod, attr)
                        if isinstance(candidate, type) and attr.endswith("LoginDriver"):
                            login_driver = candidate(
                                adb=adb,
                                search_drive=PointDrive(adb),
                            ).drive
                            break
                except ImportError:
                    pass
                if login_driver is None:
                    print(
                        json.dumps(
                            {"error": f"platform '{args.platform}' has no " "login driver module"}
                        )
                    )
                    return True
                driver = login_driver
            else:
                driver = PointDrive(adb).drive
        try:
            report = autowatch_cycle(
                args.platform,
                profile_name=args.profile or None,
                queries=args.query or None,
                webhook=args.webhook,
                max_cards=args.max,
                collect=not args.no_collect,
                driver=driver,
            )
        except ValueError as exc:
            print(json.dumps({"error": str(exc)}))
            return True
        print(json.dumps(report, ensure_ascii=False, indent=2, default=str))
        return True

    if cmd == "fetch-apk":
        from aios_core.platforms import fetch_apk

        try:
            path = fetch_apk(
                args.package,
                out_dir=args.out,
                source=args.source,
            )
        except ValueError as exc:
            print(json.dumps({"error": str(exc)}))
            return True
        print(json.dumps({"apk": path, "package": args.package}, ensure_ascii=False, indent=2))
        return True

    if cmd == "marker-check":
        from aios_core.platforms import check_platform_markers

        try:
            report = check_platform_markers(
                args.platform,
                Path(args.dump).read_text(encoding="utf-8"),
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
        navigation_hints = None
        if args.detail:
            detail_hints = DetailCalibrationAdvisor().analyze_detail(
                Path(args.detail).read_text(encoding="utf-8")
            )
        if args.messages:
            messenger_hints = DetailCalibrationAdvisor().analyze_messenger(
                Path(args.messages).read_text(encoding="utf-8")
            )
        if getattr(args, "navigation", None):
            navigation_hints = DetailCalibrationAdvisor().analyze_navigation(
                Path(args.navigation).read_text(encoding="utf-8")
            )
        hints = merge_hints(
            hints,
            detail_hints,
            messenger_hints,
            navigation=navigation_hints,
        )
        output = {"platform": args.platform, "hints": hints}
        if args.write:
            try:
                output["written"] = write_hints_to_descriptor(
                    args.platform,
                    hints,
                    directory=str(Path(args.root) / "platforms"),
                )
            except ValueError as exc:
                print(json.dumps({"error": str(exc)}))
                return True
        else:
            output["yaml_fragment"] = hints_to_yaml_doc(args.platform, hints)
        print(json.dumps(output, ensure_ascii=False, indent=2))
        return True

    if cmd == "codegen":
        import yaml

        from aios_core.platforms.parsergen import write_parser

        yaml_path = Path(args.root) / "platforms" / f"{args.platform}.yaml"
        if not yaml_path.exists():
            print(json.dumps({"error": f"descriptor not found: {yaml_path}"}))
            return True
        doc = yaml.safe_load(yaml_path.read_text(encoding="utf-8")) or {}
        hints = (doc.get("extras") or {}).get("parser_hints") or {}
        try:
            files = write_parser(
                args.platform,
                hints,
                project_root=args.root,
                android_package=doc.get("android_package") or "",
                dry_run=args.dry_run,
                overwrite=args.force,
            )
        except ValueError as exc:
            print(json.dumps({"error": str(exc)}))
            return True
        mode = "planned" if args.dry_run else "written"
        print(
            json.dumps(
                {mode: sorted(files)},
                ensure_ascii=False,
                indent=2,
            )
        )
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

    if cmd == "reels":
        from aios_core.modules.olx.adb import ADBController
        from aios_core.modules.olx.notifier import WebhookNotifier
        from aios_core.platforms import get_platform, reels_driver_for
        from aios_core.platforms.compliance import compliance_guard

        check = compliance_guard(args.platform, "collect", directory=args.directory)
        if not check["allowed"]:
            print(
                json.dumps(
                    {"error": check["reason"], "compliance": check}, ensure_ascii=False, indent=2
                )
            )
            return True
        from aios_core.platforms.reelscout import ReelsCollector
        from aios_core.platforms.resolver import resolve_profile, storage_for

        descriptor = get_platform(args.platform)
        profile = resolve_profile(args.platform, args.profile)
        adb = ADBController(
            package=descriptor.android_package,
            serial=getattr(args, "serial", None) or getattr(profile, "device_serial", None),
        )
        driver = None
        if args.open_tab:
            driver = reels_driver_for(
                args.platform,
                adb=adb,
                directory=args.directory,
            ).drive
        notifier = WebhookNotifier(url=args.webhook) if args.webhook else None
        collector = ReelsCollector(
            descriptor,
            adb=adb,
            directory=args.directory,
            driver=driver,
            notifier=notifier,
        )
        db = args.db or str(storage_for(descriptor, profile))
        storage = descriptor.storage_factory(db)
        try:
            written, cards = collector.collect_to_storage(
                storage,
                max_cards=args.max_cards,
            )
        finally:
            storage.close()
        print(
            json.dumps(
                {
                    "platform": args.platform,
                    "profile": profile.name,
                    "new": written,
                    "seen": len(cards),
                    "open_tab": bool(args.open_tab),
                    "cards": [c.to_dict() for c in cards],
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return True

    if cmd == "doctor":
        from aios_core.platforms import get_platform
        from aios_core.platforms.doctor import platform_doctor

        descriptor = get_platform(args.platform)
        report = platform_doctor(
            args.platform,
            descriptor.android_package,
            serial=getattr(args, "serial", None),
            directory=args.directory,
            report_recipe=bool(getattr(args, "calibrate_recipe", False)),
        )
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return True

    if cmd == "scaffold":
        files = scaffold_platform(
            args.name,
            args.package,
            project_root=args.root,
            description=args.description,
            locale=args.locale,
            dry_run=args.dry_run,
        )
        mode = "planned" if args.dry_run else "written"
        print(
            json.dumps(
                {mode: sorted(files)},
                ensure_ascii=False,
                indent=2,
            )
        )
        return True

    print(
        json.dumps(
            [descriptor.to_dict() for descriptor in list_platforms()],
            ensure_ascii=False,
            indent=2,
        )
    )
    return True


def _run_profiles(args) -> bool:
    """Dispatch a ``profiles`` subcommand: list, add, show, remove, or set-default.

    Returns True when the command was recognized and executed.
    """
    from aios_core.platforms import Profile, ProfileStore

    store = ProfileStore.default()
    cmd = args.profiles_command

    if cmd == "list":
        print(
            json.dumps(
                [p.to_dict() for p in store.list(args.platform)],
                ensure_ascii=False,
                indent=2,
            )
        )
        return True

    if cmd == "add":
        try:
            profile = store.add(
                Profile(
                    platform=args.platform,
                    name=args.name,
                    device_serial=args.device,
                    android_user=args.android_user,
                    db_path=args.db,
                    locale=args.locale,
                    notes=args.notes,
                    is_default=args.default,
                )
            )
        except ValueError as exc:
            print(json.dumps({"error": str(exc)}, ensure_ascii=False))
            return True
        print(json.dumps(profile.to_dict(), ensure_ascii=False, indent=2))
        return True

    if cmd == "show":
        profile = store.get(args.platform, args.name)
        if profile is None:
            print(
                json.dumps(
                    {"error": f"profile '{args.platform}:{args.name}' not found"},
                    ensure_ascii=False,
                )
            )
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
            print(
                json.dumps(
                    {"error": f"profile '{args.platform}:{args.name}' not found"},
                    ensure_ascii=False,
                )
            )
            return True
        print(json.dumps(profile.to_dict(), ensure_ascii=False, indent=2))
        return True

    return False


def _run_devices(args) -> bool:
    """Dispatch a ``devices`` subcommand: register, list, lease, waitlist,
    enqueue, cancel-wait, release, heartbeat, reap, ensure, limits, monitor,
    or fleet-run.

    Returns True when the command was recognized and executed.
    """
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
            record = pool.lease(args.profile, serial=args.serial, profile_store=store)
            if record is None:
                if args.enqueue:
                    wait_id = pool.enqueue(args.profile, priority=args.priority)
                    print(json.dumps({"queued": wait_id, "profile": args.profile}))
                    return True
                print(json.dumps({"error": "no idle device available"}, ensure_ascii=False))
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
                args.profile,
                pool=pool,
                profile_store=ProfileStore.default(),
                avd_prefix=args.avd_prefix,
            )
            if record is None:
                print(
                    json.dumps(
                        {"error": "could not lease or create a device"},
                        ensure_ascii=False,
                    )
                )
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

    if cmd == "fleet-run":
        from aios_core.modules.olx.notifier import WebhookNotifier
        from aios_core.platforms import DevicePool, FleetScheduler, ProfileStore

        store = ProfileStore.default()
        jobs = [
            {
                "platform": profile.platform,
                "profile": profile.name,
                "every_s": args.every_s,
                "queries": args.query or None,
            }
            for profile in store.list()
        ]
        # with-блок пула выше уже закрылся — открываем свой (тот же env):
        with DevicePool() as fleet_pool:
            scheduler = FleetScheduler(
                fleet_pool,
                notifier=WebhookNotifier(url=args.webhook),
            )
            print(
                json.dumps(
                    scheduler.run_due(jobs),
                    ensure_ascii=False,
                    indent=2,
                    default=str,
                )
            )
        return True

    return False


def _run_shards(args) -> bool:
    """Dispatch a ``shards`` subcommand: list, add, remove, route, unroute,
    monitor, jobs, requeue-stale, enqueue, or work.

    Returns True when the command was recognized and executed.
    """
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

    if cmd == "jobs":
        from aios_core.platforms.shardexec import ShardJobs

        with ShardJobs() as jobs:
            if getattr(args, "stats", False):
                print(
                    json.dumps(
                        jobs.stats(stale_after_s=getattr(args, "ttl", 600)),
                        ensure_ascii=False,
                        indent=2,
                    )
                )
            else:
                print(
                    json.dumps(
                        jobs.list(status=getattr(args, "status", None)),
                        ensure_ascii=False,
                        indent=2,
                    )
                )
        return True

    if cmd == "requeue-stale":
        from aios_core.platforms.shardexec import ShardJobs

        with ShardJobs() as jobs:
            moved = jobs.requeue_stale(stale_after_s=args.ttl)
        print(
            json.dumps(
                {
                    "requeued": len(moved),
                    "jobs": [
                        {
                            "id": j["id"],
                            "profile_key": j["profile_key"],
                            "requeued_age_s": j.get("requeued_age_s"),
                        }
                        for j in moved
                    ],
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return True

    if cmd == "enqueue":
        from aios_core.platforms.shardexec import ShardJobs

        payload = json.loads(args.payload) if args.payload else None
        with ShardJobs() as jobs:
            job_id = jobs.enqueue(args.profile, args.kind, payload=payload)
        print(
            json.dumps(
                {
                    "enqueued": job_id,
                    "profile_key": args.profile,
                    "kind": args.kind,
                    "note": "нода-исполнитель заберёт джобу через "
                    "`aios shards work` (pull-модель)",
                },
                ensure_ascii=False,
            )
        )
        return True

    if cmd == "work":
        from aios_core.platforms.shardexec import ShardJobs, ShardJobWorker

        with ShardJobs() as jobs:
            worker = ShardJobWorker(host=args.host, jobs=jobs)
            if args.once:
                result = worker.work_once()
                print(
                    json.dumps(
                        (
                            result
                            if result is not None
                            else {
                                "status": "idle",
                                "host": args.host,
                                "note": "нет pending-джоб для этой ноды",
                            }
                        ),
                        ensure_ascii=False,
                        indent=2,
                    )
                )
                return True
            import time as _time

            print(json.dumps({"working": True, "host": args.host, "poll_s": args.interval}))
            try:
                while True:
                    worker.work_once()
                    _time.sleep(args.interval)
            except KeyboardInterrupt:
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

    def _profile_line(profile) -> str:
        """Build one crontab line (or shard-job enqueue) for *profile*.

        Platform type determines whether it uses push-mode (``olx autowatch``),
        pull-model (``shards enqueue``), or the generic AutoWatch engine.
        """
        if getattr(args, "via_shards", False):
            # Pull-модель: cron только вешает джобы, исполняют ноды-воркеры:
            kinds = {"instagram": "autopilot"}
            kind = kinds.get(profile.platform)
            if kind is None:
                return (
                    f"# (нет builtin job kind для {profile.platform}; "
                    f"оставьте shell-cron или добавьте handler)"
                )
            return (
                f"*/{interval} * * * * cd {root} && "
                f"python3 aios_cli.py shards enqueue "
                f"--profile {profile.platform}:{profile.name} --kind {kind} "
                f">> {root}/data/jobs-{profile.key.replace(':', '_')}.log 2>&1"
            )
        if profile.platform == "olx":
            return (
                f"*/{interval} * * * * cd {root} && "
                f"python3 aios_cli.py olx autowatch --profile {profile.name}{webhook} "
                f">> {root}/data/autowatch-{profile.key.replace(':', '_')}.log 2>&1"
            )
        if profile.platform == "instagram":
            # Полный цикл под профилем: collect + Reels + Direct-flush
            # (login-drive pre-drive, публикация — отдельной guarded-задачей):
            return (
                f"*/{interval} * * * * cd {root} && "
                f"python3 aios_cli.py instagram autopilot --login "
                f"--db {root}/data/instagram-{profile.name}.sqlite "
                f">> {root}/data/autopilot-{profile.key.replace(':', '_')}.log 2>&1"
            )
        # Generic AutoWatch engine (descriptor+profile driven):
        return (
            f"*/{interval} * * * * cd {root} && "
            f"python3 aios_cli.py platforms autowatch "
            f"--platform {profile.platform} --profile {profile.name}{webhook} "
            f">> {root}/data/autowatch-{profile.key.replace(':', '_')}.log 2>&1"
        )

    entries = [(profile, _profile_line(profile)) for profile in profiles]
    if getattr(args, "shard_map", False):
        # Multi-host: липкие HRW-маршруты из ShardRouter (AIOS_SHARDS_DB).
        from aios_core.platforms import ShardRouter

        groups: dict = {}
        with ShardRouter() as router:
            for profile, line in entries:
                route = router.route_for(
                    f"{profile.platform}:{profile.name}",
                )
                key = (route["host"], route["base_url"]) if route else ("local", "")
                groups.setdefault(key, []).append(line)
        for (host, base_url), group_lines in sorted(groups.items()):
            note = f" ({base_url})" if base_url else " — без маршрута; запускать на этом хосте"
            lines.append(f"# === host: {host}{note} · профилей: {len(group_lines)} ===")
            lines.extend(group_lines)
            lines.append("")
    else:
        lines.extend(line for _, line in entries)
    monitor_note = (
        "  # pool monitor — запускать на каждом хосте" if getattr(args, "shard_map", False) else ""
    )
    lines.append(
        f"*/{interval} * * * * cd {root} && "
        f"python3 aios_cli.py devices monitor --once "
        f">> {root}/data/pool-monitor.log 2>&1{monitor_note}"
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

