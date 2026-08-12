#!/usr/bin/env python3
"""Run the commercial pipeline as a supervised, single-purpose service."""

from __future__ import annotations

import logging
import os
import signal
import threading

try:
    from .run_commercial_pipeline import execute_commercial_mission
except ImportError:  # Direct script execution places /app/scripts on sys.path.
    from run_commercial_pipeline import execute_commercial_mission

LOG = logging.getLogger("aios.commercial")
_STOP = threading.Event()


def _stop(signum: int, _frame: object) -> None:
    LOG.info("received signal %s; stopping after the current mission", signum)
    _STOP.set()


def main() -> int:
    logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"))
    signal.signal(signal.SIGTERM, _stop)
    signal.signal(signal.SIGINT, _stop)
    interval = max(60, int(os.environ.get("AIOS_COMMERCIAL_INTERVAL", "3600")))

    while not _STOP.is_set():
        try:
            execute_commercial_mission()
        except Exception:
            LOG.exception("commercial mission failed")
        _STOP.wait(interval)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
