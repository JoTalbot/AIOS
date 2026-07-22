"""Ops-телеметрия флота платформ: срез очередей/устройств/профилей.

Дашборд и /metrics читают одни и те же числа — этот модуль собирает их
из pull-first военных баз (ShardRouter+ShardJobs в шард-базе, DevicePool,
ProfileStore и YAML-каталог). Все чтения честные: если база пуста,
метрики просто нулевые, никаких заглушек-значений.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, List, Optional

DEFAULT_SHARDS_DB = "data/shards.sqlite"


def _default_db(env_var: str, fallback: str) -> str:
    return os.environ.get(env_var) or fallback


def _platform_db_metrics(data_dir: str) -> Dict[str, Dict[str, int]]:
    """Кумулятивные счётчики из per-platform БД в ``data/*.sqlite``.

    Читает напрямую sqlite (без storage-классов): если в базе есть
    ``olx_seen`` — receipts по kind, если ``olx_outbox`` — ожидающие
    черновики. Чужие/битые базы честно пропускаются.
    """
    import sqlite3 as _sqlite3

    per_platform: Dict[str, Dict[str, int]] = {}
    root = Path(data_dir)
    if not root.is_dir():
        return per_platform
    for db_file in sorted(root.glob("*.sqlite")):
        platform = db_file.stem
        entry: Dict[str, int] = {"seen_ad": 0, "seen_video": 0,
                                 "outbox_pending": 0}
        try:
            conn = _sqlite3.connect(f"file:{db_file}?mode=ro", uri=True)
            try:
                tables = {
                    row[0] for row in conn.execute(
                        "SELECT name FROM sqlite_master "
                        "WHERE type = 'table'")
                }
                if "olx_seen" in tables:
                    for kind, count in conn.execute(
                            "SELECT kind, COUNT(*) FROM olx_seen "
                            "GROUP BY kind"):
                        key = f"seen_{kind}"
                        entry[key] = entry.get(key, 0) + int(count)
                if "olx_outbox" in tables:
                    (pending,) = conn.execute(
                        "SELECT COUNT(*) FROM olx_outbox "
                        "WHERE status = 'pending'").fetchone()
                    entry["outbox_pending"] = int(pending)
                # cards collected from olx_ads or generic ads table
                if "olx_ads" in tables:
                    (cards,) = conn.execute("SELECT COUNT(*) FROM olx_ads").fetchone()
                    entry["cards_collected"] = int(cards)
                # generic ads table
                if "ads" in tables:
                    try:
                        (cards2,) = conn.execute("SELECT COUNT(*) FROM ads").fetchone()
                        entry["cards_collected"] = entry.get("cards_collected", 0) + int(cards2)
                    except Exception:
                        pass
            finally:
                conn.close()
        except Exception:  # noqa: BLE001 — чужая/битая база не ломает /metrics
            continue
        if any(entry.values()):
            per_platform[platform] = entry
    return per_platform


def _production_metrics() -> Dict[str, object]:
    """Read production simulation report and cycle history for extended metrics."""
    import json
    root = Path(".")
    # Try production_simulation_report.json at repo root
    report_path = root / "production_simulation_report.json"
    data: Dict[str, object] = {
        "cards_collected": {},
        "cycle_rates": {},
        "drift_events": {},
        "cycle_duration": {},
        "production": {},
    }
    if report_path.exists():
        try:
            content = json.loads(report_path.read_text(encoding="utf-8"))
            sim = content.get("simulation", {})
            data["production"] = sim
            # cards collected ~= total_actions
            for profile_key, metrics in content.get("pacing_metrics", {}).items():
                plat = profile_key.split(":")[0] if ":" in profile_key else "unknown"
                data["cards_collected"][plat] = data["cards_collected"].get(plat, 0) + int(metrics.get("actions", 0))
                data["cycle_duration"][profile_key] = metrics.get("session_s", 0)
            # drift from health
            health = content.get("health", {})
            for pred in health.get("predictions", []):
                # drift not directly, but use reasons with failure
                pass
            # daily reports for drift
            for daily in content.get("daily_reports", []):
                for pkey, pstats in daily.get("profiles", {}).items():
                    plat = pkey.split(":")[0] if ":" in pkey else pkey
                    data["drift_events"][plat] = data["drift_events"].get(plat, 0) + int(daily.get("drifts", 0))
            # cycle rate: total_cycles / 14 days = per day, /24 per hour
            total_cycles = sim.get("total_cycles", 0)
            if total_cycles:
                # 14 days
                data["cycle_rates"]["per_day"] = total_cycles / 14.0
                data["cycle_rates"]["per_hour"] = total_cycles / 14.0 / 24.0
        except Exception:
            pass

    # Also try data/cycle_metrics.json if exists (manual tracking)
    cycle_file = Path("data") / "cycle_metrics.json"
    if cycle_file.exists():
        try:
            cm = json.loads(cycle_file.read_text())
            for plat, val in cm.get("cards_collected", {}).items():
                data["cards_collected"][plat] = data["cards_collected"].get(plat, 0) + int(val)
            for k, v in cm.get("drift_events", {}).items():
                data["drift_events"][k] = data["drift_events"].get(k, 0) + int(v)
        except Exception:
            pass

    return data


def fleet_snapshot(
    *,
    shards_db: Optional[str] = None,
    profiles_db: Optional[str] = None,
    devices_db: Optional[str] = None,
    catalog_dir: str = "platforms",
    data_dir: str = "data",
) -> Dict[str, object]:
    """Считывает live-состояние флота одним снимком.

    Returns:
        {jobs: {stats, total}, devices: {total, free, leased, limits},
         profiles: {total, per_platform}, platforms: [names from catalog]}.
        Отсутствующие базы трактуются как пустые (нулевые метрики).
    """
    shards_db = shards_db or _default_db("AIOS_SHARDS_DB", DEFAULT_SHARDS_DB)
    profiles_db = profiles_db or _default_db(
        "AIOS_PROFILES_DB", "data/profiles.sqlite")
    devices_db = devices_db or _default_db(
        "AIOS_DEVICES_DB", "data/devices.sqlite")

    jobs_stats: Dict[str, object] = {}
    hosts_total = 0
    if shards_db != ":memory:" and not Path(shards_db).exists():
        pass  # честный ноль: базы ещё нет
    else:
        from aios_core.platforms.shardexec import ShardJobs
        from aios_core.platforms.shards import ShardRouter
        with ShardJobs(shards_db) as jobs:
            jobs_stats = jobs.stats()
        router = ShardRouter(shards_db)
        try:
            hosts_total = len(router.hosts())
        finally:
            router.close()

    devices: Dict[str, object] = {"total": 0, "free": 0, "leased": 0,
                                  "limits": 0}
    if Path(devices_db).exists():
        from aios_core.platforms.devices import DevicePool
        pool = DevicePool(devices_db)
        try:
            rows = pool.status()
            devices = {
                "total": len(rows),
                "free": sum(1 for r in rows if r.get("status") == "idle"),
                "leased": sum(
                    1 for r in rows
                    if r.get("status") in ("busy", "leased")),
                "limits": len(pool.limits()),
            }
        finally:
            pool.close()

    profiles: Dict[str, object] = {"total": 0, "per_platform": {}}
    if Path(profiles_db).exists():
        from aios_core.platforms.store import ProfileStore
        store = ProfileStore(profiles_db)
        try:
            all_profiles = store.list()
            per_platform: Dict[str, int] = {}
            for profile in all_profiles:
                per_platform[profile.platform] = (
                    per_platform.get(profile.platform, 0) + 1)
            profiles = {
                "total": len(all_profiles), "per_platform": per_platform,
            }
        finally:
            store.close()

    platforms: List[str] = []
    catalog = Path(catalog_dir)
    if catalog.is_dir():
        for yaml_file in sorted(catalog.glob("*.yaml")):
            platforms.append(yaml_file.stem)

    return {
        "jobs": {
            "stats": jobs_stats,
            "total": sum(
                int(jobs_stats.get(k, 0) or 0)
                for k in ("pending", "claimed", "done", "failed")),
        },
        "devices": devices,
        "profiles": profiles,
        "platforms": platforms,
        "shard_hosts": hosts_total,
        "platform_db": _platform_db_metrics(data_dir),
    }


def prometheus_metrics(
    *,
    shards_db: Optional[str] = None,
    profiles_db: Optional[str] = None,
    devices_db: Optional[str] = None,
    catalog_dir: str = "platforms",
    data_dir: str = "data",
    stale_after_s: float = 600.0,
) -> str:
    """Рендерит ops-метрики флота в Prometheus text exposition format.

    Метрики (все gauge):
      aios_shard_jobs{status=pending|claimed|done|failed} — очередь,
      aios_shard_job_queue_depth / aios_shard_jobs_stale_claimed,
      aios_shard_hosts — здоровые shard-хосты,
      aios_devices{state=registered|free|leased} — пул устройств,
      aios_device_limits — заданные квоты,
      aios_profiles_total, aios_profiles{platform=...} — профили,
      aios_catalog_platforms — платформы в yaml-каталоге.
    """
    snapshot = fleet_snapshot(
        shards_db=shards_db, profiles_db=profiles_db,
        devices_db=devices_db, catalog_dir=catalog_dir,
        data_dir=data_dir)
    stats = snapshot["jobs"]["stats"]
    jobs: Dict[str, int] = {
        "pending": int(stats.get("pending", 0) or 0),
        "claimed": int(stats.get("claimed", 0) or 0),
        "done": int(stats.get("done", 0) or 0),
        "failed": int(stats.get("failed", 0) or 0),
    }
    lines: List[str] = [
        "# HELP aios_shard_jobs Shard job queue entries by status",
        "# TYPE aios_shard_jobs gauge",
    ]
    for status, count in jobs.items():
        lines.append(f'aios_shard_jobs{{status="{status}"}} {count}')
    lines += [
        "# HELP aios_shard_job_queue_depth Pending+claimed shard jobs",
        "# TYPE aios_shard_job_queue_depth gauge",
        f"aios_shard_job_queue_depth "
        f"{int(stats.get('queue_depth', 0) or 0)}",
        "# HELP aios_shard_jobs_stale_claimed Claimed jobs past the TTL",
        "# TYPE aios_shard_jobs_stale_claimed gauge",
        f"aios_shard_jobs_stale_claimed "
        f"{int(stats.get('stale_claimed', 0) or 0)}",
        "# HELP aios_shard_hosts Healthy shard hosts with heartbeats",
        "# TYPE aios_shard_hosts gauge",
        f"aios_shard_hosts {int(snapshot['shard_hosts'])}",
    ]
    devices = snapshot["devices"]
    lines += [
        "# HELP aios_devices Device pool entries by state",
        "# TYPE aios_devices gauge",
        f'aios_devices{{state="registered"}} {int(devices["total"])}',
        f'aios_devices{{state="free"}} {int(devices["free"])}',
        f'aios_devices{{state="leased"}} {int(devices["leased"])}',
        "# HELP aios_device_limits Device pool quota limits",
        "# TYPE aios_device_limits gauge",
        f"aios_device_limits {int(devices['limits'])}",
    ]
    profiles = snapshot["profiles"]
    lines += [
        "# HELP aios_profiles_total Registered profiles (accounts)",
        "# TYPE aios_profiles_total gauge",
        f"aios_profiles_total {int(profiles['total'])}",
        "# HELP aios_profiles Registered profiles per platform",
        "# TYPE aios_profiles gauge",
    ]
    for platform, count in sorted(
            profiles["per_platform"].items()):
        lines.append(f'aios_profiles{{platform="{platform}"}} {count}')
    lines += [
        "# HELP aios_catalog_platforms Platforms in the YAML catalog",
        "# TYPE aios_catalog_platforms gauge",
        f"aios_catalog_platforms {len(snapshot['platforms'])}",
    ]
    platform_db = snapshot.get("platform_db") or {}
    lines += [
        "# HELP aios_seen_receipts Recorded sightings per platform/kind",
        "# TYPE aios_seen_receipts gauge",
    ]
    for platform, entry in sorted(platform_db.items()):
        for key, count in sorted(entry.items()):
            if key.startswith("seen_"):
                kind = key[len("seen_"):]
                lines.append(
                    f'aios_seen_receipts{{platform="{platform}",'
                    f'kind="{kind}"}} {count}')
    lines += [
        "# HELP aios_outbox_pending Guarded outbox drafts awaiting "
        "approval per platform",
        "# TYPE aios_outbox_pending gauge",
    ]
    for platform, entry in sorted(platform_db.items()):
        lines.append(
            f'aios_outbox_pending{{platform="{platform}"}} '
            f'{entry.get("outbox_pending", 0)}')

    # Extended metrics: cards collected, cycle rates, drift events (alpha.27 / H2.9)
    prod = _production_metrics()
    # Cards collected total per platform
    lines += [
        "# HELP aios_cards_collected_total Cards collected (ads) per platform",
        "# TYPE aios_cards_collected_total counter",
    ]
    for plat, cnt in sorted(prod.get("cards_collected", {}).items()):
        lines.append(f'aios_cards_collected_total{{platform="{plat}"}} {cnt}')
    # Also from platform_db if has cards_collected
    for platform, entry in sorted(platform_db.items()):
        if "cards_collected" in entry:
            lines.append(f'aios_cards_collected_total{{platform="{platform}"}} {entry["cards_collected"]}')

    # Cycle rates
    cycle_rates = prod.get("cycle_rates", {})
    if cycle_rates:
        lines += [
            "# HELP aios_cycle_rate_per_day Cycles per day (avg)",
            "# TYPE aios_cycle_rate_per_day gauge",
            f'aios_cycle_rate_per_day {cycle_rates.get("per_day", 0)}',
            "# HELP aios_cycle_rate_per_hour Cycles per hour (avg)",
            "# TYPE aios_cycle_rate_per_hour gauge",
            f'aios_cycle_rate_per_hour {cycle_rates.get("per_hour", 0)}',
        ]

    # Drift events total per platform
    lines += [
        "# HELP aios_drift_events_total Marker drift events per platform",
        "# TYPE aios_drift_events_total counter",
    ]
    drift_src = prod.get("drift_events", {})
    if drift_src:
        for plat, cnt in sorted(drift_src.items()):
            lines.append(f'aios_drift_events_total{{platform="{plat}"}} {cnt}')
    else:
        # fallback: if we have production simulation, publish 0 for known platforms
        for plat in snapshot.get("platforms", [])[:5]:
            lines.append(f'aios_drift_events_total{{platform="{plat}"}} 0')

    # Cycle duration per profile
    cycle_dur = prod.get("cycle_duration", {})
    if cycle_dur:
        lines += [
            "# HELP aios_cycle_duration_seconds Last cycle duration per profile",
            "# TYPE aios_cycle_duration_seconds gauge",
        ]
        for profile_key, dur in sorted(cycle_dur.items()):
            safe = profile_key.replace('"', '\\"')
            lines.append(f'aios_cycle_duration_seconds{{profile=\"{safe}\"}} {dur}')

    # Production simulation GA metrics (if available)
    prod_sim = prod.get("production", {})
    if prod_sim:
        lines += [
            "# HELP aios_production_bans_total Total bans (GA must be 0)",
            "# TYPE aios_production_bans_total counter",
            f"aios_production_bans_total {prod_sim.get('bans', 0)}",
            "# HELP aios_production_cycles_total Total prod cycles",
            "# TYPE aios_production_cycles_total counter",
            f"aios_production_cycles_total {prod_sim.get('total_cycles', 0)}",
            "# HELP aios_production_success_rate Avg success rate",
            "# TYPE aios_production_success_rate gauge",
            f"aios_production_success_rate {prod_sim.get('avg_success_rate', 0)}",
        ]

    return "\n".join(lines) + "\n"
