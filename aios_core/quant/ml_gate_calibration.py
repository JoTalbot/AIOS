"""Calibration threshold lookup for the Directional-v2 ML entry gate."""

from __future__ import annotations

import json
from pathlib import Path


def calibrated_ml_threshold(path: str) -> float | None:
    """Read q90 threshold from the calibration file; None on any failure.

    No cache on purpose: the file is read a few dozen times per 15-minute
    scan, and this host's filesystem can return identical st_mtime_ns for
    consecutive rewrites, so mtime-based caching would serve stale values.
    """

    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        return float(data.get("threshold_q90"))
    except (OSError, ValueError, TypeError):
        return None
