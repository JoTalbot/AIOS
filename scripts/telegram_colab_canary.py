#!/usr/bin/env python3
"""Canary for Colab routing and the at-most-once Telegram outbox.

The canary sends a silent ``sendMessage`` to the credential-backed owner chat,
verifies the full outbox path, and deletes the message immediately. Message
text and chat identifiers are never logged.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
import time
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tg_bot.paths import state_path

STATE_FILE = state_path("telegram_colab_canary.json")
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


def _colab_mode() -> str:
    allowed = {"active", "maintenance", "human_action_required", "disabled"}
    value = os.environ.get("AIOS_COLAB_MODE", "").strip().lower()
    if not value:
        path = Path(os.environ.get("AIOS_COLAB_MODE_FILE", "/etc/aios/colab-mode"))
        try:
            value = path.read_text(encoding="utf-8").strip().lower()
        except OSError:
            value = "active"
    return value if value in allowed else "active"


def run_canary(*, send_telegram: bool = False) -> dict:
    os.environ["LLM_CACHE"] = "0"
    started = time.monotonic()
    mode = _colab_mode()
    result = {
        "timestamp": time.time(),
        "ok": False,
        "mode": mode,
        "colab": {"ok": False, "status": mode},
        "route": {"ok": False},
        "telegram": {"status": "skipped"},
    }

    try:
        from aios_core.llm_balancer import LLMBalancer

        balancer = LLMBalancer()
        free_qwen_model = os.environ.get(
            "AIOS_FREE_QWEN_MODEL", "qwen/qwen3.6-27b"
        ).strip()
        if mode != "active":
            # Do not probe a CAPTCHA-blocked/stale tunnel while the owner has
            # explicitly placed Colab in a human-action or maintenance mode.
            balancer.providers.pop("colab", None)
        requested_model = "llama-3.1-8b-instant" if mode == "active" else free_qwen_model
        generation_started = time.monotonic()
        answer = balancer.chat(
            [{"role": "user", "content": "Ответь ровно: ok"}],
            model=requested_model,
            system="Ответь кратко.",
            max_tokens=4,
            temperature=0,
            task_type="chat",
        )
        generation_sec = time.monotonic() - generation_started
        route = dict(balancer.last_route)
        provider = str(route.get("provider") or "unknown")
        model = str(route.get("model") or "unknown")
        colab_ok = (
            bool(answer.strip())
            and provider == "colab"
            and model == "colab/qwen2.5-coder"
        )
        managed_qwen_ok = (
            bool(answer.strip())
            and provider == "groq"
            and model == free_qwen_model
        )
        route_ok = colab_ok if mode == "active" else managed_qwen_ok
        result["colab"] = {
            "ok": colab_ok,
            "status": "active" if colab_ok else mode,
        }
        result["route"] = {
            "ok": route_ok,
            "provider": provider,
            "model": model,
            "generation_sec": round(generation_sec, 3),
        }
    except Exception as exc:
        result["route"] = {"ok": False, "error_class": type(exc).__name__}

    from tg_bot.credentials import secret_from_env_or_credential

    token = secret_from_env_or_credential(
        "AIOS_TELEGRAM_TOKEN", "TELEGRAM_BOT_TOKEN", credential="telegram_token"
    )
    owner_chat = secret_from_env_or_credential(
        "TELEGRAM_CHAT_ID", credential="telegram_owner_chat_id"
    ).split(",", 1)[0].strip()
    if send_telegram and token and owner_chat:
        try:
            from tg_bot.api import TelegramAPI
            from tg_bot.outbox import TelegramOutbox

            api = TelegramAPI(token)
            dedup_key = f"canary:{time.time_ns()}"
            outbox = TelegramOutbox(api, state_path("telegram_canary_outbox.sqlite3"))
            outbox.start()
            send_started = time.monotonic()
            queued = outbox.enqueue(
                dedup_key=dedup_key,
                chat_id=int(owner_chat),
                text=(
                    "✅ AIOS canary: LLM route и Telegram outbox работают."
                    if result["route"]["ok"]
                    else "⚠️ AIOS canary: требуемый LLM route недоступен."
                ),
                parse_mode="",
                generation_sec=float(result["route"].get("generation_sec", 0)),
                provider=str(result["route"].get("provider", "unknown")),
                model=str(result["route"].get("model", "unknown")),
                disable_notification=True,
                metric_event="canary_delivery",
            )
            row = outbox.wait(dedup_key, timeout=25)
            outbox.stop()
            status = row.get("status") if row else "timeout"
            deleted = False
            message_id = int(row.get("telegram_message_id") or 0) if row else 0
            if status == "sent" and message_id:
                for attempt in range(3):
                    try:
                        api.delete_message(int(owner_chat), message_id)
                        deleted = True
                        break
                    except Exception:
                        if attempt < 2:
                            time.sleep(1)
                if not deleted:
                    status = "delete_failed"
            result["telegram"] = {
                "status": status,
                "queued": queued,
                "deleted": deleted,
                "send_sec": round(time.monotonic() - send_started, 3),
                "attempts": int(row.get("attempts", 0)) if row else 0,
            }
        except Exception as exc:
            result["telegram"] = {"status": "failed", "error_class": type(exc).__name__}
    elif token:
        # Dry mode still verifies DNS, IPv4 transport, TLS and authentication.
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
    result["ok"] = bool(result["route"]["ok"] and telegram_ok)
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
                "provider": result["route"].get("provider", "unknown"),
                "model": result["route"].get("model", "unknown"),
                "gen_sec": result["route"].get("generation_sec", 0),
                "send_sec": result["telegram"].get(
                    "send_sec", result["telegram"].get("api_sec", 0)
                ),
                "total_sec": result["total_sec"],
                "error_class": result["route"].get("error_class", ""),
                "timestamp": result["timestamp"],
            }
        )
    except Exception:
        pass

    # Safe one-line status: no chat id, endpoint, prompt, token or answer.
    print(
        "canary_status=" + ("ok" if result["ok"] else "failed")
        + f" mode={result['mode']}"
        + f" provider={result['route'].get('provider', 'unknown')}"
        + f" model={result['route'].get('model', 'unknown')}"
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
