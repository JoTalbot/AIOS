"""Shared retention selection for timestamped history records (v11.14.0).

Both the substrate convergence engine (dispatch_history, v11.13.0) and
the energy-aware scheduler (_dispatches, v11.14.0) keep append-only
lists of timestamped records. This module centralises the retention
semantics so preview/purge pairs in both subsystems select records
identically:

* ``keep_last`` alone drops everything but the newest N records;
* ``older_than_seconds`` alone drops records older than the age cutoff;
* combined, a record survives when it is within the newest ``keep_last``
  entries OR newer than the cutoff (protected union).

Append order is chronological (records are appended with time.time()),
so "newest N" is simply the last N positions.
"""

from __future__ import annotations

import time
from typing import Any

__all__ = ["RetentionMaintenanceEngine", "plan_retention_purge"]


def plan_retention_purge(
    records: list[Any],
    keep_last: int | None = None,
    older_than_seconds: float | None = None,
    timestamp_of: Any = None,
    age_criterion_name: str = "older_than_seconds",
) -> tuple[float | None, int, list[int]]:
    """Validate retention criteria and compute the purge selection.

    Args:
        records: history records; dicts with a numeric ``timestamp`` by
            default, or anything else when ``timestamp_of`` is given
            (e.g. ``MemoryEntry`` objects with ``created_at``).
        keep_last: protect the newest N records (None = unprotected).
        older_than_seconds: drop records older than this age in seconds
            (None = no age criterion).
        timestamp_of: optional accessor ``record -> float`` overriding
            the default ``record["timestamp"]`` (v11.14.0 worked with
            dicts only; v11.15.0 generalised for object stores).
        age_criterion_name: how the age criterion is named in validation
            error messages (callers converting other units, e.g. days,
            pass their public parameter name).

    Returns:
        (cutoff_timestamp, protected_count, removed_indices) — the age
        cutoff (None without an age criterion), how many records are
        protected by keep_last, and the record indices to remove.

    Raises:
        ValueError: no criterion given, keep_last not an int >= 0, or
            older_than_seconds not a positive number.
    """
    if keep_last is None and older_than_seconds is None:
        raise ValueError(f"at least one retention criterion (keep_last or {age_criterion_name}) is required")
    if keep_last is not None:
        if isinstance(keep_last, bool) or not isinstance(keep_last, int):
            raise ValueError("keep_last must be an integer")
        if keep_last < 0:
            raise ValueError("keep_last must be >= 0")
    cutoff: float | None = None
    if older_than_seconds is not None:
        try:
            window = float(older_than_seconds)
        except (TypeError, ValueError):
            raise ValueError(f"{age_criterion_name} must be a number") from None
        if window <= 0:
            raise ValueError(f"{age_criterion_name} must be positive")
        cutoff = time.time() - window

    if timestamp_of is None:

        def timestamp_of(record: Any) -> float:
            if isinstance(record, dict):
                val = record.get("timestamp", record.get("created_at", 0.0))
            else:
                val = getattr(record, "timestamp", getattr(record, "created_at", 0.0))
            try:
                return float(val)
            except (TypeError, ValueError):
                return 0.0

    total = len(records)
    protected: set[int] = set()
    if keep_last:
        protected = set(range(max(0, total - keep_last), total))
    removed: list[int] = []
    for index, record in enumerate(records):
        if index in protected:
            continue
        if cutoff is not None and timestamp_of(record) >= cutoff:
            continue
        removed.append(index)
    return cutoff, len(protected), removed


class RetentionMaintenanceEngine:
    """Unified background retention maintenance across all history stores (v11.16.0)."""

    def __init__(
        self,
        engine: Any = None,
        scheduler: Any = None,
        memory_system: Any = None,
    ) -> None:
        self.engine = engine
        self.scheduler = scheduler
        self.memory_system = memory_system
        self.last_run: dict[str, Any] | None = None

    def run_maintenance_cycle(
        self,
        keep_last_history: int | None = 1000,
        keep_last_dispatches: int | None = 1000,
        keep_last_archive: int | None = 500,
        older_than_seconds: float | None = 604800.0,
    ) -> dict[str, Any]:
        """Execute maintenance retention purges across configured subsystems."""
        results: dict[str, Any] = {}
        total_purged = 0

        if self.engine is not None and hasattr(self.engine, "purge_history"):
            try:
                res = self.engine.purge_history(
                    keep_last=keep_last_history,
                    older_than_seconds=older_than_seconds,
                    confirm=True,
                )
                results["engine_history"] = res
                total_purged += res.get("removed", 0)
            except Exception as err:
                results["engine_history"] = {"error": str(err)}

        if self.scheduler is not None and hasattr(self.scheduler, "purge_dispatches"):
            try:
                res = self.scheduler.purge_dispatches(
                    keep_last=keep_last_dispatches,
                    older_than_seconds=older_than_seconds,
                    confirm=True,
                )
                results["scheduler_dispatches"] = res
                total_purged += res.get("removed", 0)
            except Exception as err:
                results["scheduler_dispatches"] = {"error": str(err)}

        if self.memory_system is not None and hasattr(self.memory_system, "purge_archive"):
            older_days = older_than_seconds / 86400.0 if older_than_seconds else None
            try:
                res = self.memory_system.purge_archive(
                    keep_last=keep_last_archive,
                    older_than_days=older_days,
                    confirm=True,
                )
                results["memory_archive"] = res
                total_purged += res.get("removed", 0)
            except Exception as err:
                results["memory_archive"] = {"error": str(err)}

        report = {
            "timestamp": time.time(),
            "total_records_purged": total_purged,
            "subsystems": results,
        }
        self.last_run = report
        return report
