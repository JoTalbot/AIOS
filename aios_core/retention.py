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

__all__ = ["plan_retention_purge"]


def plan_retention_purge(
    records: list[dict[str, Any]],
    keep_last: int | None = None,
    older_than_seconds: float | None = None,
) -> tuple[float | None, int, list[int]]:
    """Validate retention criteria and compute the purge selection.

    Args:
        records: dispatch/history records with a numeric ``timestamp``.
        keep_last: protect the newest N records (None = unprotected).
        older_than_seconds: drop records older than this age in seconds
            (None = no age criterion).

    Returns:
        (cutoff_timestamp, protected_count, removed_indices) — the age
        cutoff (None without an age criterion), how many records are
        protected by keep_last, and the record indices to remove.

    Raises:
        ValueError: no criterion given, keep_last not an int >= 0, or
            older_than_seconds not a positive number.
    """
    if keep_last is None and older_than_seconds is None:
        raise ValueError("at least one retention criterion (keep_last or older_than_seconds) is required")
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
            raise ValueError("older_than_seconds must be a number") from None
        if window <= 0:
            raise ValueError("older_than_seconds must be positive")
        cutoff = time.time() - window

    total = len(records)
    protected: set[int] = set()
    if keep_last:
        protected = set(range(max(0, total - keep_last), total))
    removed: list[int] = []
    for index, record in enumerate(records):
        if index in protected:
            continue
        if cutoff is not None and record.get("timestamp", 0.0) >= cutoff:
            continue
        removed.append(index)
    return cutoff, len(protected), removed
