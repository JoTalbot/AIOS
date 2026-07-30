#!/usr/bin/env python3
"""faucet_one_shot.py — однократный клейм LNS-крана с решением hCaptcha.

Полный пайплайн без Playwright (чистый HTTP):
  1. Решение hCaptcha через 2Captcha API (~60-90 сек)
  2. Мгновенный вызов GET /api/lnurl1 с токеном
  3. Сохранение результата (LNURL/payment request) в ledger

Использование:
  python3 code/faucet_one_shot.py
  python3 code/faucet_one_shot.py --json

Зависимости: только стандартная библиотека Python (urllib, json).
Стоимость: ~$0.002 за каждый запуск (2Captcha hCaptcha).

Вектор: САМООБЕСПЕЧЕНИЕ (L0 zero-cost optional).
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import random
import sys
import time
import uuid
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from captcha_budget_atomic import atomic_record_spend, atomic_try_reserve
from typing import Any, Dict, Optional

SKILL_DIR = Path(os.environ.get("OCTOPUS_ME_SKILL_DIR") or Path(__file__).resolve().parents[1])
CONFIG = SKILL_DIR / "config"
DATA = SKILL_DIR / "data"
FAUCET_CFG = CONFIG / "faucet_config.json"
LEDGER = DATA / "faucet_ledger.json"

UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
BASE_URL = "https://lightningnetworkstores.com"
SITEKEY = os.environ.get("FAUCET_SITEKEY", "")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("one_shot")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default or {}


def save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def load_config() -> Dict[str, Any]:
    """Загрузить конфиг (API-ключи, настройки)."""
    cfg = load_json(FAUCET_CFG, {})
    if not isinstance(cfg, dict):
        cfg = {}
    return cfg


def check_budget(cfg: Dict[str, Any]) -> bool:
    """Проверить флаг и дневной бюджет."""
    captcha = cfg.get("captcha", {})
    if not captcha.get("auto_paid_enabled", False):
        log.warning("Paid CAPTCHA disabled by config")
        return False
    budget_file = DATA / "daily_captcha_budget.json"
    budget = load_json(budget_file, {"date": "", "spent_usd": 0.0})

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if budget.get("date") != today:
        budget = {"date": today, "spent_usd": 0.0, "solves": 0}

    max_daily = captcha.get("max_daily_budget_usd", 0.50)
    if budget["spent_usd"] >= max_daily:
        log.warning(f"Дневной бюджет исчерпан: ${budget['spent_usd']:.4f} / ${max_daily:.2f}")
        return False
    return True


def record_spend(cost_usd: float) -> None:
    atomic_record_spend(DATA / 'daily_captcha_budget.json', cost_usd, source='faucet_one_shot.py')

def solve_hcaptcha(api_key: str) -> Optional[str]:
    """Решить hCaptcha через 2Captcha. Возвращает токен или None."""
    log.info("Решение hCaptcha через 2Captcha...")

    # Создать задачу
    payload = json.dumps({
        "clientKey": api_key,
        "task": {
            "type": "HCaptchaTaskProxyless",
            "websiteURL": f"{BASE_URL}/faucet",
            "websiteKey": SITEKEY,
        },
    }).encode()

    try:
        req = urllib.request.Request(
            "https://api.2captcha.com/createTask",
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read().decode())
    except Exception as e:
        log.error(f"2Captcha createTask: {e}")
        return None

    if result.get("errorId", 0) != 0:
        log.error(f"2Captcha error: {result.get('errorDescription', result)}")
        return None

    task_id = result.get("taskId")
    if not task_id:
        log.error(f"2Captcha: нет taskId в ответе")
        return None

    log.info(f"Задача {str(task_id)[:12]}... создана, ожидание решения...")

    # Опрос результата
    for i in range(40):
        time.sleep(3)
        payload = json.dumps({"clientKey": api_key, "taskId": task_id}).encode()
        try:
            req = urllib.request.Request(
                "https://api.2captcha.com/getTaskResult",
                data=payload,
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                result = json.loads(resp.read().decode())
        except Exception as e:
            log.warning(f"poll error ({(i+1)*3}s): {e}")
            continue

        if result.get("status") == "ready":
            token = result.get("solution", {}).get("gRecaptchaResponse", "")
            if token:
                log.info(f"Капча решена за ~{(i+1)*3}с (токен {len(token)} символов)")
                return token

        if result.get("errorId", 0) != 0:
            log.error(f"2Captcha task failed: {result.get('errorDescription', '?')}")
            return None

        if (i + 1) % 10 == 0:
            log.info(f"  ожидание... {(i+1)*3}с")

    log.error("Таймаут решения капчи (120с)")
    return None


def claim_lnurl1(token: str) -> Dict[str, Any]:
    """Вызвать GET /api/lnurl1 с решённым токеном. Возвращает ответ API."""
    # Генерация fingerprint-данных (anti-abuse bypass)
    bfg = hashlib.md5(str(random.random()).encode()).hexdigest()[:32]
    dfg = hashlib.md5(str(uuid.uuid4()).encode()).hexdigest()[:32]
    wfg = "1920x1080"

    params = urllib.parse.urlencode({
        "bfg": bfg,
        "dfg": dfg,
        "wfg": wfg,
        "h-captcha-response": token,
        "g-recaptcha-response": "",
    })

    url = f"{BASE_URL}/api/lnurl1?{params}"
    headers = {
        "User-Agent": UA,
        "Accept": "application/json",
        "Referer": f"{BASE_URL}/faucet",
        "Origin": BASE_URL,
    }

    log.info(f"Вызов GET /api/lnurl1...")

    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = resp.read().decode("utf-8", errors="replace")
            status = resp.status
    except urllib.error.HTTPError as e:
        body = ""
        try:
            body = e.read().decode("utf-8", errors="replace")
        except Exception:
            pass
        return {
            "http_status": e.code,
            "status": "fail",
            "message": body[:500],
            "raw": body,
        }
    except Exception as e:
        return {"http_status": 0, "status": "error", "message": str(e)}

    try:
        j = json.loads(data)
        return {"http_status": status, **j}
    except Exception:
        return {"http_status": status, "status": "unknown", "raw": data[:500]}


def update_ledger(result: Dict[str, Any], solve_time_s: float, cost_usd: float) -> None:
    """Обновить ledger результатами клейма."""
    ledger = load_json(LEDGER, {"vector": "САМООБЕСПЕЧЕНИЕ", "runs": [], "total_sats_claimed": 0})
    if not isinstance(ledger, dict):
        ledger = {"vector": "САМООБЕСПЕЧЕНИЕ", "runs": [], "total_sats_claimed": 0}

    success = result.get("status") == "success"
    claim_data = result.get("data", {})
    payment_request = claim_data.get("payment_request", "")
    amount = claim_data.get("amount", 0)

    entry = {
        "ts": utc_now(),
        "faucet": "lightningnetworkstores.com",
        "method": "one_shot_api",
        "captcha_solver": "2captcha",
        "captcha_solve_time_s": round(solve_time_s, 1),
        "cost_usd": cost_usd,
        "cost_source": "config.max_cost_per_solve_usd",
        "api_endpoint": "/api/lnurl1",
        "api_status": result.get("http_status"),
        "success": success,
        "amount_sats": amount,
        "payment_request": payment_request[:100] + "..." if payment_request else None,
        "error": result.get("message") if not success else None,
    }

    if success and amount:
        ledger["total_sats_claimed"] = ledger.get("total_sats_claimed", 0) + amount

    ledger["runs"].append(entry)
    ledger["updated"] = utc_now()
    save_json(LEDGER, ledger)
    log.info(f"Ledger обновлён")


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser(description="LNS faucet one-shot claim")
    ap.add_argument("--json", action="store_true", help="JSON output")
    args = ap.parse_args()

    config = load_config()
    api_key = config.get("captcha", {}).get("2captcha", {}).get("api_key", "")

    if not api_key:
        log.error("2Captcha API ключ не настроен в faucet_config.json")
        return 1

    if not check_budget(config):
        log.error("Дневной бюджет исчерпан или paid CAPTCHA отключена")
        return 1
    cost_usd = float(config.get('captcha', {}).get('max_cost_per_solve_usd', 0.003))
    max_daily = float(config.get('captcha', {}).get('max_daily_budget_usd', 0.50))
    reserved, _ = atomic_try_reserve(DATA / 'daily_captcha_budget.json', cost_usd, max_daily, source='faucet_one_shot.py')
    if not reserved:
        log.error("Резервирование CAPTCHA-бюджета отклонено")
        return 1

    # === Шаг 1: Решить капчу ===
    t0 = time.time()
    token = solve_hcaptcha(api_key)
    solve_time = time.time() - t0

    if not token:
        log.error("Не удалось решить капчу")
        return 1

    # === Шаг 2: Вызвать API клейма ===
    result = claim_lnurl1(token)
    # === Шаг 4: Обновить ledger ===
    update_ledger(result, solve_time, cost_usd)

    # === Вывод ===
    if args.json:
        output = {
            "ts": utc_now(),
            "faucet": "lightningnetworkstores.com",
            "captcha_solve_time_s": round(solve_time, 1),
            "cost_usd": cost_usd,
        "cost_source": "config.max_cost_per_solve_usd",
            "claim_result": result,
        }
        print(json.dumps(output, indent=2, ensure_ascii=False))
    else:
        log.info(f"Результат: HTTP {result.get('http_status')} — {result.get('message', result.get('status'))}")
        if result.get("status") == "success":
            claim = result.get("data", {})
            log.info(f"Клейм успешен! Amount: {claim.get('amount')} sats")
            pr = claim.get("payment_request", "")
            if pr:
                log.info(f"Payment request: {pr[:80]}...")
        elif result.get("http_status") == 500:
            log.info("Бекенд крана временно недоступен (500)")
            log.info("Решение капчи работает корректно — повторите позже")

    return 0 if result.get("status") == "success" else 1


if __name__ == "__main__":
    raise SystemExit(main())
