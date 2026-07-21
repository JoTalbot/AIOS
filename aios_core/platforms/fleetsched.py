"""FleetScheduler — планировщик autowatch-циклов платформ по пулу устройств.

Многие платформы × много профилей × ограниченный пул эмуляторов:
FleetScheduler запускает джобы (``platform/profile``) по их интервалам,
арендуя устройство из DevicePool на время цикла и освобождая после.

* интервалы и метки последних запусков — в kv пула (``pool_limits``,
  общий SQLite пула);
* runner инъецируется (по умолчанию —
  :func:`autowatch_cycle`; получает device serial аренды);
* занято → честный ``skipped-busy`` (конкуренция через механику пула,
  а не lock-файлы);
* runner вернул ``marker_status == "drift"`` → webhook-алёрт
  ``marker-drift`` через WebhookNotifier (независим от autowatch-
  уведомлений канал).
"""

from __future__ import annotations

import time
from typing import Callable, Dict, List, Optional

from aios_core.modules.olx.notifier import WebhookNotifier

LastRunKey = "fleet:last_run:"


class FleetScheduler:
    """Запускает due-джобы платформ на арендованных устройствах.

    Args:
        pool: DevicePool (общий SQLite — аренды видны всем узлам).
        notifier: WebhookNotifier для drift-алёртов (без URL — no-op).
        now: фабрика времени (тесты).
    """

    def __init__(
        self,
        pool,
        notifier: Optional[WebhookNotifier] = None,
        now: Callable[[], float] = time.time,
    ):
        self.pool = pool
        self.notifier = notifier or WebhookNotifier(url=None)
        self._now = now

    def _last_run(self, platform: str, profile: str) -> float:
        return float(
            self.pool.limit(f"{LastRunKey}{platform}:{profile}", 0) or 0
        )

    def due_jobs(self, jobs: List[Dict]) -> List[Dict]:
        """Джобы, интервал которых истёк (или не запускались)."""
        now = self._now()
        return [
            job for job in jobs
            if now - self._last_run(job["platform"], job["profile"]) >=
            float(job.get("every_s", 900))
        ]

    def run_due(
        self,
        jobs: List[Dict],
        runner: Optional[Callable] = None,
    ) -> Dict[str, object]:
        """Исполняет все due-джобы; манифест результатов.

        Args:
            jobs: список {platform, profile, every_s?, queries?}.
            runner: callable(platform, profile, serial) → dict|None;
                None → autowatch_cycle (без collect, если джоб
                ``queries`` пуст — хранилищный пересчёт).

        Returns:
            {ran, skipped_busy, errors, drifts, results: [...]}
        """
        from aios_core.platforms.autowatch import autowatch_cycle

        results: List[Dict[str, object]] = []
        for job in self.due_jobs(jobs):
            platform = job["platform"]
            profile = job["profile"]
            lease_key = f"{platform}:{profile}"
            lease = self.pool.lease(lease_key)
            if lease is None:
                results.append({
                    "job": lease_key, "status": "skipped-busy",
                })
                continue
            serial = lease["serial"]
            entry: Dict[str, object] = {"job": lease_key,
                                        "serial": serial}
            try:
                if runner is not None:
                    report = runner(platform, profile, serial=serial)
                else:
                    report = autowatch_cycle(
                        platform, profile_name=profile,
                        queries=job.get("queries") or None,
                        collect=bool(job.get("queries")),
                    )
                entry["status"] = "ran"
                if isinstance(report, dict):
                    entry["report_keys"] = sorted(report)
                    if report.get("marker_status") == "drift":
                        entry["drift"] = True
                        self.notifier.send("marker-drift", {
                            "platform": platform, "profile": profile,
                            "hint": "recalibrate: calibrate --write && "
                                    "codegen --force",
                        })
            except Exception as exc:  # noqa: BLE001 — изолируем джоб
                entry["status"] = "error"
                entry["error"] = str(exc)[:200]
            finally:
                self.pool.release(lease_key)
                self.pool.set_limit(
                    f"{LastRunKey}{platform}:{profile}",
                    int(self._now()),
                )
            results.append(entry)

        return {
            "ran": sum(1 for r in results if r["status"] == "ran"),
            "skipped_busy": sum(
                1 for r in results if r["status"] == "skipped-busy"
            ),
            "errors": sum(1 for r in results if r["status"] == "error"),
            "drifts": sum(1 for r in results if r.get("drift")),
            "results": results,
        }
