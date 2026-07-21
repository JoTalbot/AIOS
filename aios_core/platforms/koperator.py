"""AIOS K8s operator: watch-loop CRD (Platform/Profile/Job) → fleet state.

Тонкий контроллер без kopf: стандартный reconcile подаётся списком
custom objects (в проде — из Kubernetes Watch API), применяет их к
AIOS-флоту:

* ``Platform``  → регистрация yaml-дескриптора в ``platforms/``;
* ``Profile``   → запись в ProfileStore (sqlite);
* ``Job``       → enqueue в ShardJobs (pull-модель воркеров).

Guarded-семантика не размывается: оператор только материализует
желаемое состояние; отправки/постинг остаются за outbox/confirm/
compliance на уровне платформ. ``python -m aios_core.platforms.koperator``
— точка входа Deployment'а (здесь: честный отказ без API-сервера).
"""

from __future__ import annotations

import json
import os
import sys
from typing import Dict, List, Optional

_KIND_HANDLERS = ("Platform", "Profile", "Job")


def _apply_platform(spec: Dict, directory: str) -> Dict[str, str]:
    """Материализует Platform CR → platforms/<name>.yaml."""
    import yaml

    name = spec["name"]
    doc = {
        "name": name,
        "android_package": spec["androidPackage"],
        "agent_module": spec.get("agentModule",
                                 f"aios_core.modules.{name}"),
        "storage_class": spec.get(
            "storageClass",
            f"aios_core.modules.{name}.storage."
            f"{name.capitalize()}Storage"),
        "adb_class": spec.get("adbClass",
                              "aios_core.modules.olx.adb.ADBController"),
        "default_locale": spec.get("locale", "uk-UA"),
        "extras": {
            "compliance": spec.get("compliance") or {
                "autopost_allowed": False,
                "messenger": "approval-only",
                "collector": False,
                "note": "deny-by-default (кластерный CR)",
            },
            "parser_hints": {},
        },
    }
    from pathlib import Path
    root = Path(directory)
    root.mkdir(parents=True, exist_ok=True)
    path = root / f"{name}.yaml"
    path.write_text(yaml.safe_dump(doc, allow_unicode=True),
                    encoding="utf-8")
    return {"written": str(path)}


def _apply_profile(spec: Dict, store) -> Dict[str, str]:
    """Profile CR → ProfileStore entry (идемпотентный upsert)."""
    from aios_core.platforms.profile import Profile

    platform, name = spec["platformRef"], spec["name"]
    if store.get(platform, name) is not None:
        store.update(
            platform, name,
            device_serial=spec.get("deviceSerial"),
            is_default=bool(spec.get("default")),
        )
        return {"updated": f"{platform}:{name}"}
    profile = Profile(
        platform=platform, name=name,
        device_serial=spec.get("deviceSerial"),
        is_default=bool(spec.get("default")),
    )
    store.add(profile)
    return {"registered": f"{platform}:{name}"}


def _apply_job(spec: Dict, jobs) -> Dict[str, int]:
    """Job CR → ShardJobs.enqueue."""
    job_id = jobs.enqueue(
        spec["profileKey"], spec["kind"], payload=spec.get("payload"))
    return {"enqueued": int(job_id)}


def reconcile(
    objects: List[Dict],
    *,
    directory: str = "platforms",
    profiles_db: str = ":memory:",
    shards_db: str = ":memory:",
) -> Dict[str, object]:
    """Один цикл сверки: применить пачку объектов, вернуть отчёт.

    Args:
        objects: список K8s-объектов {kind, metadata, spec}.
        directory: каталог дескрипторов (Platform → yaml).
        profiles_db: путь базы профилей.
        shards_db: путь базы shard jobs.

    Returns:
        {applied: {Platform: n, Profile: n, Job: n}, errors: [...]}.
    """
    from aios_core.platforms.shardexec import ShardJobs
    from aios_core.platforms.store import ProfileStore

    applied: Dict[str, int] = {kind: 0 for kind in _KIND_HANDLERS}
    errors: List[str] = []
    store = ProfileStore(profiles_db)
    jobs = ShardJobs(shards_db)
    try:
        for obj in objects:
            kind = obj.get("kind", "")
            spec = obj.get("spec") or {}
            meta = obj.get("metadata") or {}
            label = f"{kind}/{meta.get('name', '?')}"
            try:
                if kind == "Platform":
                    result = _apply_platform(spec, directory)
                elif kind == "Profile":
                    result = _apply_profile(spec, store)
                elif kind == "Job":
                    result = _apply_job(spec, jobs)
                else:
                    errors.append(f"{label}: unknown kind")
                    continue
                applied[kind] += 1
            except Exception as exc:  # noqa: BLE001 — честный список ошибок
                errors.append(f"{label}: {exc}")
                result = None
    finally:
        store.close()
        jobs.close()
    return {"applied": applied, "errors": errors}


_K8S_GROUP = "aios.io/v1alpha1"


def watch_once_from_api(
    api_base: str,
    namespace: str,
    *,
    token: Optional[str] = None,
    opener=None,
) -> List[Dict]:
    """List-запрос CR в кластере (K8s REST, без SDK).

    В тестах подменяется ``opener`` (urllib-like). В проде отдаёт
    список objects совместимый с :func:`reconcile`.
    """
    import urllib.request

    headers = {"Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    items: List[Dict] = []
    for plural in ("platforms", "profiles", "jobs"):
        url = (f"{api_base}/apis/{_K8S_GROUP}/namespaces/"
               f"{namespace}/{plural}")
        request = urllib.request.Request(url, headers=headers)
        open_fn = opener or urllib.request.urlopen
        with open_fn(request) as response:
            items.extend(json.loads(response.read()).get("items", []))
    return items


def main() -> int:
    """Точка входа Deployment'а: без API-сервера честно сообщаем конфиг."""
    api_base = os.environ.get("AIOS_K8S_API")
    namespace = os.environ.get("AIOS_K8S_NAMESPACE", "aios-fleet")
    if not api_base:
        print(json.dumps({
            "error": "AIOS_K8S_API не задан — оператор вне кластера "
                     "(ожидается https://kubernetes.default.svc)"}, ))
        return 2
    objects = watch_once_from_api(api_base, namespace)
    report = reconcile(
        objects,
        profiles_db=os.environ.get("AIOS_PROFILES_DB",
                                   "/var/lib/aios/profiles.sqlite"),
        shards_db=os.environ.get("AIOS_SHARDS_DB",
                                 "/var/lib/aios/shards.sqlite"),
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if not report["errors"] else 1


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
