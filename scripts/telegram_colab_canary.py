#!/usr/bin/env python3
"""Canary for Colab routing and the at-most-once Telegram outbox.

Set ``TELEGRAM_CANARY_CHAT_ID`` to a dedicated technical chat.  When omitted,
Colab is still checked but no Telegram activity is produced.  The regular owner
chat is deliberately not used as an implicit default.
"""

from __future__ import annotations

import argparse
import json
import os
import tempfile
import time
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
STATE_FILE = ROOT / "data" / "telegram_colab_canary.json"
load_dotenv(ROOT / ".env")


def _atomic_state(payload: dict) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=STATE_FILE.name + ".", dir=str(STATE_FILE.parent))
    tmp = Path(name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, STATE_FILE)
    finally:
        tmp.unlink(missing_ok=True)


def _previous_state() -> dict:
    try:
        value = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError):
        return {}


def run_canary(*, send_telegram: bool = False) -> dict:
    os.environ["LLM_CACHE"] = "0"
    started = time.monotonic()
    result = {
        "timestamp": time.time(),
        "ok": False,
        "colab": {"ok": False},
        "telegram": {"status": "skipped"},
    }

    try:
        from aios_core.llm_balancer import LLMBalancer

        balancer = LLMBalancer()
        generation_started = time.monotonic()
        answer = balancer.chat(
            [{"role": "user", "content": "Ответь ровно: ok"}],
            model="llama-3.1-8b-instant",
            system="Ответь кратко.",
            max_tokens=4,
            temperature=0,
            task_type="chat",
        )
        generation_sec = time.monotonic() - generation_started
        route = dict(balancer.last_route)
        provider = str(route.get("provider") or "unknown")
        model = str(route.get("model") or "unknown")
        colab_ok = bool(answer.strip()) and provider == "colab" and model == "colab/qwen2.5-coder"
        result["colab"] = {
            "ok": colab_ok,
            "provider": provider,
            "model": model,
            "generation_sec": round(generation_sec, 3),
        }
    except Exception as exc:
        result["colab"] = {"ok": False, "error_class": type(exc).__name__}

    token = os.environ.get("AIOS_TELEGRAM_TOKEN") or os.environ.get("TELEGRAM_BOT_TOKEN")
    canary_chat = os.environ.get("TELEGRAM_CANARY_CHAT_ID", "").strip()
    if send_telegram and token and canary_chat:
        try:
            from tg_bot.api import TelegramAPI
            from tg_bot.outbox import TelegramOutbox

            api = TelegramAPI(token)
            action_started = time.monotonic()
            api.send_chat_action(int(canary_chat))
            action_sec = time.monotonic() - action_started
            bucket = int(time.time() // 600)
            outbox = TelegramOutbox(api, ROOT / "data" / "telegram_canary_outbox.sqlite3")
            outbox.start()
            queued = outbox.enqueue(
                dedup_key=f"canary:{bucket}",
                chat_id=int(canary_chat),
                text=(
                    "✅ AIOS canary: Colab/Qwen и Telegram outbox работают."
                    if result["colab"]["ok"]
                    else "⚠️ AIOS canary: Colab/Qwen использовал fallback или недоступен."
                ),
                parse_mode="",
                generation_sec=float(result["colab"].get("generation_sec", 0)),
                provider=str(result["colab"].get("provider", "unknown")),
                model=str(result["colab"].get("model", "unknown")),
            )
            row = outbox.wait(f"canary:{bucket}", timeout=25)
            outbox.stop()
            result["telegram"] = {
                "status": row.get("status") if row else "timeout",
                "queued": queued,
                "typing_sec": round(action_sec, 3),
                "attempts": int(row.get("attempts", 0)) if row else 0,
            }
        except Exception as exc:
            result["telegram"] = {"status": "failed", "error_class": type(exc).__name__}
    elif token:
        # A dedicated canary chat is optional. getMe still verifies Telegram
        # DNS, IPv4 transport, TLS and bot authentication without user-visible spam.
        try:
            from tg_bot.api import TelegramAPI

            api_started = time.monotonic()
            payload = TelegramAPI(token).get_me()
            result["telegram"] = {
                "status": "api_ok" if payload.get("ok") else "failed",
                "api_sec": round(time.monotonic() - api_started, 3),
            }
        except Exception as exc:
            result["telegram"] = {"status": "failed", "error_class": type(exc).__name__}
    else:
        result["telegram"] = {"status": "missing_token"}

    telegram_ok = result["telegram"]["status"] in ("api_ok", "sent")
    result["ok"] = bool(result["colab"]["ok"] and telegram_ok)
    previous = _previous_state()
    result["consecutive_failures"] = (
        0 if result["ok"] else int(previous.get("consecutive_failures", 0)) + 1
    )
    result["total_sec"] = round(time.monotonic() - started, 3)
    _atomic_state(result)

    try:
        from tg_bot.metrics import record_telegram_event

        record_telegram_event(
            {
                "event": "canary",
                "source": "telegram_colab_canary",
                "status": "sent" if result["ok"] else "failed",
                "provider": result["colab"].get("provider", "unknown"),
                "model": result["colab"].get("model", "unknown"),
                "gen_sec": result["colab"].get("generation_sec", 0),
                "send_sec": result["telegram"].get(
                    "typing_sec", result["telegram"].get("api_sec", 0)
                ),
                "total_sec": result["total_sec"],
                "error_class": result["colab"].get("error_class", ""),
                "timestamp": result["timestamp"],
            }
        )
    except Exception:
        pass

    # Safe one-line status: no chat id, endpoint, prompt, token or answer.
    print(
        "canary_status=" + ("ok" if result["ok"] else "failed")
        + f" provider={result['colab'].get('provider', 'unknown')}"
        + f" model={result['colab'].get('model', 'unknown')}"
        + f" telegram={result['telegram']['status']}"
        + f" total={result['total_sec']:.2f}s"
    )
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--send-telegram",
        action="store_true",
        default=os.environ.get("CANARY_SEND_TELEGRAM", "0").lower() in ("1", "true", "yes"),
    )
    args = parser.parse_args()
    raise SystemExit(0 if run_canary(send_telegram=args.send_telegram)["ok"] else 1)
