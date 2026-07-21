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


def fleet_snapshot(
    *,
    shards_db: Optional[str] = None,
    profiles_db: Optional[str] = None,
    devices_db: Optional[str] = None,
    catalog_dir: str = "platforms",
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
    }


def prometheus_metrics(
    *,
    shards_db: Optional[str] = None,
    profiles_db: Optional[str] = None,
    devices_db: Optional[str] = None,
    catalog_dir: str = "platforms",
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
        devices_db=devices_db, catalog_dir=catalog_dir)
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
    return "\n".join(lines) + "\n"
