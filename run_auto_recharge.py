#!/usr/bin/env python3
"""
AIOS Auto-Recharge & API Balance Monitor Daemon
Скрипт автоматического мониторинга баланса LLM API ключей (OpenRouter) и пополнения из бюджета системы.
"""

import sys
import os
import time
import argparse
import logging
import json
import urllib.request
from pathlib import Path

# Убедимся, что корень проекта импортируем
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Если запущен в докере, используем /app, иначе /root/AIOS
data_dir = "/root/AIOS/data"
is_docker = os.path.exists('/.dockerenv') or (os.path.exists('/proc/self/cgroup') and 'docker' in open('/proc/self/cgroup').read())
if is_docker and os.path.exists("/app/data"):
    data_dir = "/app/data"

from aios_core.crypto_wallet import AIOSWalletManager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("AIOS.AutoRecharge")


def _get_keys_from_env() -> list[str]:
    """Считывает все API ключи OpenRouter из файла .env."""
    keys = []
    env_file = PROJECT_ROOT / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("OPENROUTER_API_KEY") or line.startswith("LLM_API_KEY"):
                parts = line.split("=", 1)
                if len(parts) == 2:
                    k = parts[1].strip().strip('"').strip("'")
                    if k and k not in keys and k.startswith("sk-or-"):
                        keys.append(k)
    return keys


def check_openrouter_balance(api_key: str) -> dict:
    """Запрашивает статус ключа и его лимиты через OpenRouter API."""
    url = "https://openrouter.ai/api/v1/auth/key"
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {api_key}",
            "User-Agent": "AIOS-Balance-Monitor/1.0"
        }
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return {
                "status": "success",
                "key_label": data.get("data", {}).get("label", "")[:12] + "...",
                "usage_usd": float(data.get("data", {}).get("usage", 0.0)),
                "is_free_tier": bool(data.get("data", {}).get("is_free_tier", False)),
                "limit_remaining": data.get("data", {}).get("limit_remaining")
            }
    except Exception as e:
        logger.error(f"Ошибка запроса OpenRouter API: {e}")
        return {"status": "error", "error": str(e)}


def run_recharge_monitor() -> dict:
    logger.info("📡 [AutoRecharge] Запуск проверки баланса LLM API ключей...")
    
    keys = _get_keys_from_env()
    if not keys:
        logger.warning("⚠️ Не найдено ключей OpenRouter во внешнем файле .env.")
        return {"status": "no_keys"}
        
    wallet_mgr = AIOSWalletManager(data_dir)
    ledger = wallet_mgr.load_ledger()
    system_budget = ledger.get("distribution_shares_usd", {}).get("system", 0.0)
    
    reports = []
    alerts_triggered = []
    
    for idx, key in enumerate(keys, 1):
        status = check_openrouter_balance(key)
        if status.get("status") == "success":
            logger.info(
                f"🔑 Ключ #{idx} ({status['key_label']}): "
                f"Использовано: ${status['usage_usd']:.4f} | Free Tier: {status['is_free_tier']}"
            )
            reports.append({
                "key_index": idx,
                "label": status["key_label"],
                "usage_usd": status["usage_usd"],
                "is_free_tier": status["is_free_tier"],
                "limit_remaining": status["limit_remaining"]
            })
            
            # Если ключ на бесплатном тарифе (Free Tier) или лимит исчерпан
            if status["is_free_tier"]:
                alerts_triggered.append({
                    "key_index": idx,
                    "label": status["key_label"],
                    "reason": "Ключ находится на бесплатном тарифе (Free Tier) и имеет жесткие лимиты/ошибки 402."
                })
        else:
            reports.append({"key_index": idx, "status": "error", "error": status.get("error")})
            
    # Форматируем аларм для Telegram, если обнаружена нехватка баланса
    alarm_msg = ""
    if alerts_triggered:
        logger.warning(f"🚨 [AutoRecharge] Обнаружены ограничения баланса на {len(alerts_triggered)} ключах!")
        
        lines = [
            "🚨 <b>Внимание! Лимиты ИИ-ключей OpenRouter ограничены!</b>",
            f"Текущий автономный бюджет Системы: <b>${system_budget:.2f} USD</b>\n"
        ]
        for alt in alerts_triggered:
            lines.append(f"• Ключ #{alt['key_index']} (<code>{alt['label']}</code>): {alt['reason']}")
            
        lines.append(
            "\nРекомендуется пополнить баланс аккаунта.\n"
            "Вы можете инициировать пополнение командой: <code>оплати openrouter</code>"
        )
        alarm_msg = "\n".join(lines)
        
        # Записываем состояние предупреждения
        alert_state_file = Path(data_dir) / "autonomy_alert_state.json"
        alert_state_file.write_text(json.dumps({
            "last_alert_at": time.time(),
            "alert_message": alarm_msg,
            "status": "pending_recharge"
        }, ensure_ascii=False, indent=2), encoding="utf-8")

    return {
        "status": "success",
        "keys_checked_count": len(keys),
        "keys_reports": reports,
        "alerts_triggered": alerts_triggered,
        "system_budget_available_usd": system_budget,
        "telegram_alarm_message": alarm_msg
    }


if __name__ == "__main__":
    res = run_recharge_monitor()
    print("\n" + "=" * 50)
    print("=== AIOS AUTO-RECHARGE & BALANCE MONITOR RESULTS ===")
    print("=" * 50)
    print(json.dumps(res, indent=2, ensure_ascii=False))
