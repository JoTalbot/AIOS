#!/usr/bin/env python3
"""Evaluate Telegram metrics and emit a deduplicated alert after two bad windows."""

from __future__ import annotations

import json
import os
import sys
import tempfile
import time
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tg_bot.metrics import summarize_telegram_metrics

STATE = ROOT / "data" / "telegram_metrics_alert_state.json"
load_dotenv(ROOT / ".env")


def _load_state() -> dict:
    try:
        value = json.loads(STATE.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError):
        return {}


def _save_state(value: dict) -> None:
    STATE.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=STATE.name + ".", dir=str(STATE.parent))
    tmp = Path(name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, STATE)
    finally:
        tmp.unlink(missing_ok=True)


def evaluate(summary: dict) -> list[str]:
    if int(summary.get("events", 0)) < 3:
        return []
    reasons = []
    if float(summary.get("success_rate", 1)) < float(os.environ.get("TELEGRAM_MIN_SUCCESS_RATE", "0.95")):
        reasons.append("success_rate")
    latency = summary.get("latency", {})
    if float(latency.get("send_p95", 0)) > float(os.environ.get("TELEGRAM_MAX_SEND_P95", "5")):
        reasons.append("send_p95")
    providers = summary.get("providers", {})
    routed = sum(int(value) for name, value in providers.items() if name not in ("unknown", "deterministic"))
    colab_share = int(providers.get("colab", 0)) / routed if routed else 1.0
    if colab_share < float(os.environ.get("TELEGRAM_MIN_COLAB_SHARE", "0.80")):
        reasons.append("colab_share")
    return reasons


def main() -> int:
    summary = summarize_telegram_metrics(hours=float(os.environ.get("TELEGRAM_METRICS_WINDOW_HOURS", "1")))
    reasons = evaluate(summary)
    previous = _load_state()
    consecutive = int(previous.get("consecutive_degraded", 0)) + 1 if reasons else 0
    state = {
        "timestamp": time.time(),
        "consecutive_degraded": consecutive,
        "reasons": reasons,
        "summary": summary,
    }
    _save_state(state)

    alert_status = "not_needed"
    chat = os.environ.get("TELEGRAM_ALERT_CHAT_ID", "").strip() or os.environ.get(
        "TELEGRAM_CANARY_CHAT_ID", ""
    ).strip()
    from tg_bot.credentials import secret_from_env_or_credential

    token = secret_from_env_or_credential(
        "AIOS_TELEGRAM_TOKEN", "TELEGRAM_BOT_TOKEN", credential="telegram_token"
    )
    if consecutive >= 2 and reasons and chat and token:
        try:
            from tg_bot.api import TelegramAPI
            from tg_bot.outbox import TelegramOutbox

            bucket = int(time.time() // 3600)
            outbox = TelegramOutbox(
                TelegramAPI(token), ROOT / "data" / "telegram_alert_outbox.sqlite3"
            )
            outbox.start()
            key = f"metrics-alert:{bucket}:" + ",".join(sorted(reasons))
            outbox.enqueue(
                dedup_key=key,
                chat_id=int(chat),
                text=(
                    "⚠️ AIOS Telegram/LLM деградация подтверждена в двух окнах: "
                    + ", ".join(reasons)
                    + f". send p95={summary['latency']['send_p95']:.2f}s, "
                    + f"success={summary['success_rate']:.1%}."
                ),
                parse_mode="",
                provider="metrics",
                model="alert",
            )
            row = outbox.wait(key, timeout=25)
            outbox.stop()
            alert_status = row.get("status", "timeout") if row else "timeout"
        except Exception as exc:
            alert_status = "failed:" + type(exc).__name__

    print(
        f"metrics_status={'degraded' if reasons else 'ok'} consecutive={consecutive} "
        f"reasons={','.join(reasons) or 'none'} alert={alert_status}"
    )
    return 1 if consecutive >= 2 and reasons else 0


if __name__ == "__main__":
    raise SystemExit(main())
