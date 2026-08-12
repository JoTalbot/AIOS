#!/usr/bin/env python3
"""Atomically render redacted Telegram/Colab metrics for the Docker sidecar."""

from __future__ import annotations

import argparse
import os
import signal
import sys
import tempfile
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tg_bot.metrics import render_telegram_prometheus

DEFAULT_OUTPUT = Path("/var/lib/aios-telegram-metrics/metrics.prom")
_STOP = threading.Event()


def write_snapshot(path: Path = DEFAULT_OUTPUT) -> None:
    payload = render_telegram_prometheus().encode("utf-8")
    path.parent.mkdir(parents=True, exist_ok=True)
    os.chmod(path.parent, 0o755)
    fd, name = tempfile.mkstemp(prefix=path.name + ".", dir=str(path.parent))
    tmp = Path(name)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(tmp, 0o644)
        os.replace(tmp, path)
    finally:
        tmp.unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--interval", type=float, default=10.0)
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()

    def stop(_signum: int, _frame: object) -> None:
        _STOP.set()

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    while True:
        write_snapshot(args.output)
        if args.once or _STOP.wait(max(1.0, args.interval)):
            return 0


if __name__ == "__main__":
    raise SystemExit(main())
