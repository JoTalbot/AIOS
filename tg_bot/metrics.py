"""Structured Telegram/LLM latency metrics without message contents or secrets."""

from __future__ import annotations

import json
import os
import tempfile
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
METRICS_FILE = ROOT / "data" / "telegram_metrics.jsonl"
SUMMARY_FILE = ROOT / "data" / "telegram_metrics_summary.json"
_LOCK = threading.Lock()
_ALLOWED = {
    "event",
    "status",
    "provider",
    "model",
    "gen_sec",
    "send_sec",
    "total_sec",
    "attempts",
    "error_class",
    "timestamp",
    "source",
}


def _atomic_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=path.name + ".", dir=str(path.parent))
    tmp = Path(name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, path)
    finally:
        tmp.unlink(missing_ok=True)


def _percentile(values: list[float], percentile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, round((len(ordered) - 1) * percentile)))
    return round(float(ordered[index]), 3)


def record_telegram_event(event: dict, path: Path | None = None) -> None:
    """Append one redacted metric and refresh a compact 24-hour summary."""
    if os.environ.get("TELEGRAM_METRICS_ENABLED", "1").lower() in ("0", "false", "no", "off"):
        return
    target = path or METRICS_FILE
    clean = {key: value for key, value in event.items() if key in _ALLOWED}
    clean.setdefault("timestamp", time.time())
    clean.setdefault("event", "telegram_send")
    target.parent.mkdir(parents=True, exist_ok=True)
    with _LOCK:
        with target.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(clean, ensure_ascii=False, separators=(",", ":")) + "\n")
        if target == METRICS_FILE:
            _atomic_json(SUMMARY_FILE, summarize_telegram_metrics(hours=24, path=target))


def summarize_telegram_metrics(hours: float = 24, path: Path | None = None) -> dict:
    target = path or METRICS_FILE
    cutoff = time.time() - max(0.0, hours) * 3600
    rows: list[dict] = []
    try:
        for line in target.read_text(encoding="utf-8").splitlines()[-10000:]:
            try:
                row = json.loads(line)
            except ValueError:
                continue
            if float(row.get("timestamp", 0)) >= cutoff:
                rows.append(row)
    except OSError:
        pass

    # Delivery SLOs are calculated from real telegram_send events only. Canary
    # failures are tracked separately and must not poison one hour of user-send
    # success metrics after an expected Colab recovery.
    deliveries = [row for row in rows if row.get("event") == "telegram_send"]
    canaries = [row for row in rows if row.get("event") == "canary"]
    sent = [row for row in deliveries if row.get("status") == "sent"]
    providers: dict[str, int] = {}
    errors: dict[str, int] = {}
    for row in deliveries:
        provider = str(row.get("provider") or "unknown")
        providers[provider] = providers.get(provider, 0) + 1
        if row.get("status") != "sent":
            error = str(row.get("error_class") or row.get("status") or "unknown")
            errors[error] = errors.get(error, 0) + 1

    def nums(name: str) -> list[float]:
        return [float(row.get(name, 0)) for row in sent]

    return {
        "window_hours": hours,
        "generated_at": time.time(),
        "total_events": len(rows),
        "events": len(deliveries),
        "canary_events": len(canaries),
        "canary_failures": sum(1 for row in canaries if row.get("status") != "sent"),
        "sent": len(sent),
        "failed": len(deliveries) - len(sent),
        "success_rate": round(len(sent) / len(deliveries), 4) if deliveries else 1.0,
        "providers": providers,
        "errors": errors,
        "latency": {
            "gen_p50": _percentile(nums("gen_sec"), 0.50),
            "gen_p95": _percentile(nums("gen_sec"), 0.95),
            "send_p50": _percentile(nums("send_sec"), 0.50),
            "send_p95": _percentile(nums("send_sec"), 0.95),
            "total_p50": _percentile(nums("total_sec"), 0.50),
            "total_p95": _percentile(nums("total_sec"), 0.95),
        },
    }
