"""Calibration threshold helpers for the Directional-v2 ML entry gate."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Sequence

import numpy as np

# Sanity band for a deployable q90 threshold. Outside of it the model's
# probability distribution is degenerate and the gate would be meaningless.
CALIBRATION_BAND = (0.40, 0.90)


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


def compute_quantiles(prob_up: Sequence[float]) -> dict[str, float]:
    """Quantiles of the model's prob_up distribution (single source of truth)."""

    arr = np.asarray(prob_up, dtype=float)
    if arr.size == 0:
        return {"q50": 0.5, "q75": 0.5, "q90": 0.5, "q95": 0.5, "q99": 0.5}
    return {
        "q50": round(float(np.quantile(arr, 0.50)), 4),
        "q75": round(float(np.quantile(arr, 0.75)), 4),
        "q90": round(float(np.quantile(arr, 0.90)), 4),
        "q95": round(float(np.quantile(arr, 0.95)), 4),
        "q99": round(float(np.quantile(arr, 0.99)), 4),
    }


def threshold_is_sane(threshold: float) -> bool:
    """True when the q90 threshold is inside the deployable band."""

    lo, hi = CALIBRATION_BAND
    return lo <= threshold <= hi
