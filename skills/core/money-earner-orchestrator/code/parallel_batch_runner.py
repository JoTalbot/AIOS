#!/usr/bin/env python3
"""parallel_batch_runner.py — параллельный батчевый сбор со всех кранов.

Архитектура:
  Phase 1 — PROBE (параллельно): проверить живость всех кранов, обнаружить sitekey
  Phase 2 — SOLVE (параллельно): решить капчи для всех captcha_solvable кранов
  Phase 3 — CLAIM (параллельно): вызвать API клейма для каждого решённого
  Phase 4 — REPORT: сохранить результаты в ledger

Запуск:
  python3 code/parallel_batch_runner.py              # один батч
  python3 code/parallel_batch_runner.py --loop       # бесконечный цикл (каждые N мин)
  python3 code/parallel_batch_runner.py --loop --json # JSON лог
  python3 code/parallel_batch_runner.py --once-only  # выйти если нечего делать
"""
from __future__ import annotations

import concurrent.futures
import hashlib
import json
import logging
import os
import random
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from captcha_budget_atomic import atomic_record_spend, atomic_try_reserve, atomic_refund
from typing import Any, Dict, List, Optional, Tuple

SKILL_DIR = Path(os.environ.get("OCTOPUS_ME_SKILL_DIR") or Path(__file__).resolve().parents[1])
CONFIG = SKILL_DIR / "config"
DATA = SKILL_DIR / "data"
FAUCET_CFG = CONFIG / "faucet_config.json"
LEDGER = DATA / "faucet_ledger.json"
CATALOG_FILE = CONFIG / "faucet_catalog.json"

UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("batch_runner")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default if default is not None else {}


def save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def load_config() -> Dict[str, Any]:
    return load_json(FAUCET_CFG, {})


def load_catalog() -> List[Dict[str, Any]]:
    cfg = load_json(CATALOG_FILE, {})
    if isinstance(cfg, dict) and isinstance(cfg.get("faucets"), list):
        return cfg["faucets"]
    return []


# ============================================================
# PHASE 1: PROBE — параллельная проверка живости
# ============================================================

def probe_one(faucet: Dict[str, Any]) -> Dict[str, Any]:
    """Проверить один кран. Быстрый HTTP GET без Playwright."""
    url = faucet.get("url", "")
    fid = faucet.get("id", "?")
    captcha_type = faucet.get("captcha_type", "unknown")
    sitekey = faucet.get("captcha_sitekey", "")

    result = {
        "id": fid,
        "url": url,
        "alive": False,
        "http_status": 0,
        "has_captcha": False,
        "has_lnurl": False,
        "has_lightning": False,
        "captcha_sitekey": sitekey,
        "mechanism": faucet.get("mechanism", "unknown"),
        "auth_required": faucet.get("auth_required", False),
        "network": faucet.get("network", "mainnet"),
        "integration_status": faucet.get("integration_status", "unknown"),
        "integration_note": faucet.get("integration_note", ""),
    }

    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=12) as resp:
            html = resp.read().decode("utf-8", errors="replace")
            result["alive"] = True
            result["http_status"] = resp.status
            result["html_len"] = len(html)

            low = html.lower()
            result["has_captcha"] = bool(
                "hcaptcha" in low or "h-captcha" in low
                or "g-recaptcha" in low or "turnstile" in low
            )
            result["has_lnurl"] = "lnurl" in low
            result["has_lightning"] = "lightning" in low

            # Если есть hCaptcha но нет sitekey в каталоге — попытаемся извлечь
            if result["has_captcha"] and not sitekey:
                m = re.search(r'data-sitekey=["\']([\w-]+)["\']', html)
                if m:
                    result["captcha_sitekey"] = m.group(1)
                else:
                    m = re.search(r'sitekey["\s:]+["\']([\w-]+)["\']', html)
                    if m:
                        result["captcha_sitekey"] = m.group(1)

            # Обновить mechanism
            if "lnurl" in low:
                result["mechanism"] = "lnurl_withdraw"
            elif "lightning address" in low:
                result["mechanism"] = "lightning_address"

    except urllib.error.HTTPError as e:
        result["http_status"] = e.code
        result["alive"] = e.code < 500
    except Exception as e:
        result["error"] = str(e)[:80]

    return result


def classify_probe(p: Dict[str, Any]) -> str:
    if p.get("integration_status") in {"not_a_faucet", "disabled", "deprecated"}:
        return "excluded"
    if not p.get("alive"):
        return "dead"
    if p.get("network") == "testnet":
        return "testnet_useless"
    if p.get("auth_required"):
        return "auth_required"
    # captcha_sitekey из каталога (проверен ранее deep-probe) — приоритет
    if p.get("captcha_sitekey"):
        return "captcha_solvable"
    # JS-loaded captcha обнаружена в HTML
    if p.get("has_captcha"):
        if p.get("captcha_sitekey"):
            return "captcha_solvable"
        return "captcha_blocked"
    if p.get("has_lnurl") or p.get("has_lightning"):
        return "claimable"
    return "needs_investigation"


def phase_probe(faucets: List[Dict]) -> List[Dict]:
    """Параллельный probe всех кранов."""
    log.info(f"Phase PROBE: {len(faucets)} кранов, параллельно...")
    results = []
    with ThreadPoolExecutor(max_workers=10) as pool:
        futures = {pool.submit(probe_one, f): f for f in faucets}
        for future in as_completed(futures):
            r = future.result()
            r["claim_class"] = classify_probe(r)
            results.append(r)
            icon = {"captcha_solvable": ">>", "claimable": "OK", "dead": "XX",
                     "auth_required": "AU", "captcha_blocked": "XC"}.get(r["claim_class"], "??")
            log.info(f"  [{icon}] {r['id']:<24} HTTP={r['http_status']} "
                     f"cap={r['has_captcha']} key={bool(r['captcha_sitekey'])} ln={r['has_lnurl']}")
    return results


# ============================================================
# PHASE 2: SOLVE — параллельное решение капч
# ============================================================

def solve_one_captcha(faucet: Dict, api_key: str) -> Tuple[str, Optional[str], bool]:
    """Решить hCaptcha для одного крана. Возвращает (faucet_id, token|None)."""
    fid = faucet.get("id")
    sitekey = faucet.get("captcha_sitekey", "")
    url = faucet.get("url", "")

    if not sitekey:
        return fid, None, False

    log.info(f"  [{fid}] Решение капчи (sitekey={sitekey[:16]}...)")
    t0 = time.time()

    try:
        # Создать задачу
        payload = json.dumps({
            "clientKey": api_key,
            "task": {
                "type": "HCaptchaTaskProxyless",
                "websiteURL": url,
                "websiteKey": sitekey,
            }
        }).encode()
        req = urllib.request.Request(
            "https://api.2captcha.com/createTask",
            data=payload, headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            result = json.loads(resp.read().decode())

        task_id = result.get("taskId")
        if not task_id or result.get("errorId", 0) != 0:
            log.warning(f"  [{fid}] createTask fail: {result.get('errorDescription', '?')}")
            return fid, None, False

        # Опрос
        for i in range(30):
            time.sleep(3)
            payload = json.dumps({"clientKey": api_key, "taskId": task_id}).encode()
            req = urllib.request.Request(
                "https://api.2captcha.com/getTaskResult",
                data=payload, headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=60) as resp:
                result = json.loads(resp.read().decode())

            if result.get("status") == "ready":
                token = result.get("solution", {}).get("gRecaptchaResponse", "")
                if token:
                    elapsed = time.time() - t0
                    log.info(f"  [{fid}] SOLVED in {elapsed:.0f}s")
                    return fid, token, True

            if result.get("errorId", 0) != 0:
                log.warning(f"  [{fid}] Task failed")
                return fid, None, True

        log.warning(f"  [{fid}] Timeout 90s")
        return fid, None, True

    except Exception as e:
        log.error(f"  [{fid}] Error: {e}")
        return fid, None, True


def phase_solve(probes: List[Dict], config: Dict) -> Dict[str, str]:
    """Параллельно решить капчи для всех captcha_solvable кранов."""
    api_key = config.get("captcha", {}).get("2captcha", {}).get("api_key", "")
    if not api_key:
        log.error("Нет 2Captcha API ключа!")
        return {}

    solvable = [p for p in probes if p.get("claim_class") == "captcha_solvable"]
    # Canary paid mode: exclude sources with known repeated negative ROI and cap to one paid task per wave.
    blocked_ids = {"lns-faucet", "dogefaucet-com"}
    solvable = [p for p in solvable if p.get("id") not in blocked_ids]
    max_paid_per_wave = int(config.get("captcha", {}).get("max_paid_per_wave", 1))
    solvable = solvable[:max_paid_per_wave]
    if not solvable:
        log.info("Phase SOLVE: нет captcha_solvable кранов")
        return {}

    # Бюджет
    budget_file = DATA / "daily_captcha_budget.json"
    budget = load_json(budget_file, {"date": "", "spent_usd": 0.0, "solves": 0})
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if budget.get("date") != today:
        budget = {"date": today, "spent_usd": 0.0, "solves": 0}

    max_daily = config.get("captcha", {}).get("max_daily_budget_usd", 0.50)
    max_per = config.get("captcha", {}).get("max_cost_per_solve_usd", 0.003)
    remaining = int((max_daily - budget["spent_usd"]) / max_per)

    if remaining <= 0:
        log.warning(f"Бюджет исчерпан: ${budget['spent_usd']:.4f}/${max_daily}")
        return {}

    # Ограничить параллельность по бюджету
    to_solve = solvable[:min(remaining, max_paid_per_wave)]

    log.info(f"Phase SOLVE: {len(to_solve)} кранов параллельно (бюджет на ~{remaining} решений)")

    # Атомарно резервировать бюджет до отправки каждой платной CAPTCHA-задачи.
    reserved_faucets = []
    for faucet in to_solve:
        ok, budget = atomic_try_reserve(
            budget_file,
            max_per,
            max_daily,
            source="parallel_batch_runner.py",
            solves=1,
        )
        if not ok:
            log.warning(f"  [{faucet['id']}] CAPTCHA budget reservation rejected")
            continue
        reserved_faucets.append(faucet)

    tokens = {}
    with ThreadPoolExecutor(max_workers=min(len(reserved_faucets), 5) or 1) as pool:
        futures = {pool.submit(solve_one_captcha, f, api_key): f for f in reserved_faucets}
        for future in as_completed(futures):
            fid, token, task_created = future.result()
            if token:
                tokens[fid] = token
            elif not task_created:
                budget = atomic_refund(
                    budget_file,
                    max_per,
                    source="parallel_batch_runner.py",
                    solves=1,
                    reason=f"{fid}:task_not_created",
                )
                log.info(f"  [{fid}] reservation refunded: task not created")

    solved_count = len(tokens)
    budget = load_json(budget_file, {"date": "", "spent_usd": 0.0, "solves": 0})

    log.info(f"Phase SOLVE: {solved_count}/{len(to_solve)} решено, "
             f"бюджет ${budget['spent_usd']:.4f}/${max_daily}")
    return tokens


# ============================================================
# PHASE 3: CLAIM — параллельный клейм
# ============================================================

def claim_lnurl(faucet: Dict, token: str, config: Dict) -> Dict[str, Any]:
    """Клейм для LNS-типа крана (GET /api/lnurl1 с параметрами)."""
    fid = faucet.get("id")
    url = faucet.get("url", "")
    bfg = hashlib.md5(str(random.random()).encode()).hexdigest()[:32]
    dfg = hashlib.md5(str(uuid.uuid4()).encode()).hexdigest()[:32]

    params = urllib.parse.urlencode({
        "bfg": bfg, "dfg": dfg, "wfg": "1920x1080",
        "h-captcha-response": token,
        "g-recaptcha-response": "",
    })

    base = urllib.parse.urlparse(url).netloc
    scheme = urllib.parse.urlparse(url).scheme
    claim_url = f"{scheme}://{base}/api/lnurl1?{params}"

    headers = {
        "User-Agent": UA, "Accept": "application/json",
        "Referer": url, "Origin": f"{scheme}://{base}",
    }

    try:
        req = urllib.request.Request(claim_url, headers=headers)
        with urllib.request.urlopen(req, timeout=60) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            j = json.loads(body)
            return {
                "faucet_id": fid, "http_status": resp.status,
                "status": j.get("status"), "message": j.get("message", ""),
                "data": j.get("data"), "ts": utc_now(),
            }
    except urllib.error.HTTPError as e:
        body = ""
        try:
            body = e.read().decode("utf-8", errors="replace")[:300]
        except Exception:
            pass
        return {
            "faucet_id": fid, "http_status": e.code,
            "status": "fail", "message": body,
            "ts": utc_now(),
        }
    except Exception as e:
        return {"faucet_id": fid, "http_status": 0,
                "status": "error", "message": str(e), "ts": utc_now()}


def phase_claim(probes: List[Dict], tokens: Dict[str, str], config: Dict) -> List[Dict]:
    """Параллельный клейм всех решённых кранов."""
    if not tokens:
        log.info("Phase CLAIM: нет токенов для клейма")
        return []

    # Маппинг: faucet_id -> probe data
    probe_map = {p["id"]: p for p in probes}

    log.info(f"Phase CLAIM: {len(tokens)} кранов параллельно...")
    results = []
    with ThreadPoolExecutor(max_workers=len(tokens)) as pool:
        futures = {}
        for fid, token in tokens.items():
            faucet_data = probe_map.get(fid, {})
            futures[pool.submit(claim_lnurl, faucet_data, token, config)] = fid

        for future in as_completed(futures):
            fid = futures[future]
            try:
                result = future.result()
            except Exception as e:
                result = {"faucet_id": fid, "status": "error", "message": str(e)}
            results.append(result)

            status = result.get("status", "?")
            http = result.get("http_status", 0)
            icon = "OK" if status == "success" else "ERR"
            msg = result.get("message", "")[:60]
            log.info(f"  [{icon}] {fid}: HTTP {http} — {msg}")

            if status == "success":
                d = result.get("data", {})
                amt = d.get("amount", 0)
                pr = d.get("payment_request", "")
                if amt:
                    log.info(f"       *** {amt} sats! Invoice: {pr[:60]}...")
                    result["sats_claimed"] = amt

    return results


# ============================================================
# PHASE 4: REPORT
# ============================================================

def phase_report(probes: List[Dict], claims: List[Dict], solve_time: float) -> Dict:
    """Сформировать отчёт и обновить ledger."""
    summary = {}
    for p in probes:
        cc = p.get("claim_class", "unknown")
        summary[cc] = summary.get(cc, 0) + 1

    total_sats = sum(c.get("sats_claimed", 0) for c in claims)
    success_count = sum(1 for c in claims if c.get("status") == "success")

    report = {
        "ts": utc_now(),
        "mode": "parallel_batch",
        "vector": "САМООБЕСПЕЧЕНИЕ",
        "phase_times_s": {
            "probe": "parallel",
            "solve": round(solve_time, 1),
            "claim": "parallel",
        },
        "probed": len(probes),
        "classification": summary,
        "captcha_solved": len([c for c in claims if c.get("http_status") not in (0,)]),
        "claims_attempted": len(claims),
        "claims_success": success_count,
        "total_sats_claimed": total_sats,
        "claims": claims,
    }

    # Ledger
    ledger = load_json(LEDGER, {"vector": "САМООБЕСПЕЧЕНИЕ", "runs": [], "total_sats_claimed": 0})
    if not isinstance(ledger, dict):
        ledger = {"vector": "САМООБЕСПЕЧЕНИЕ", "runs": [], "total_sats_claimed": 0}

    ledger["runs"].append(report)
    ledger["total_sats_claimed"] = ledger.get("total_sats_claimed", 0) + total_sats
    ledger["updated"] = utc_now()
    save_json(LEDGER, ledger)

    return report


def print_report(report: Dict):
    """Красивый вывод отчёта."""
    print(f"\n{'='*55}")
    print(f"  BATCH RUN {report['ts']}")
    print(f"{'='*55}")
    print(f"  Probe: {report['probed']} кранов (параллельно)")
    print(f"  Классификация: {report['classification']}")
    print(f"  Попыток клейма: {report['claims_attempted']}")
    print(f"  Успешных: {report['claims_success']}")
    print(f"  Всего sats: {report['total_sats_claimed']}")
    if report["claims"]:
        print(f"\n  Результаты клеймов:")
        for c in report["claims"]:
            fid = c.get("faucet_id", "?")
            st = c.get("status", "?")
            http = c.get("http_status", 0)
            msg = c.get("message", "")[:50]
            sats = c.get("sats_claimed", 0)
            extra = f" {sats} sats" if sats else ""
            print(f"    {fid}: HTTP {http} {st}{extra} — {msg}")
    print(f"{'='*55}\n")


# ============================================================
# MAIN LOOP
# ============================================================

def run_batch(config: Dict) -> Dict:
    """Один полный батч: probe → solve → claim → report."""
    batch_start = time.time()

    # Phase 1
    faucets = load_catalog()
    probes = phase_probe(faucets)

    # Phase 2
    t_solve_start = time.time()
    tokens = phase_solve(probes, config)
    solve_time = time.time() - t_solve_start

    # Phase 3
    claims = phase_claim(probes, tokens, config)

    # Phase 4
    report = phase_report(probes, claims, solve_time)

    batch_time = time.time() - batch_start
    log.info(f"Батч завершён за {batch_time:.0f}s")

    return report


def main():
    import argparse
    ap = argparse.ArgumentParser(description="Parallel batch faucet runner")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--loop", action="store_true", help="Бесконечный цикл")
    ap.add_argument("--interval", type=int, default=30, help="Интервал между батчами (мин)")
    ap.add_argument("--once-only", action="store_true", help="Выйти если нечего делать")
    args = ap.parse_args()

    config = load_config()

    run_count = 0
    while True:
        run_count += 1
        log.info(f"\n{'#'*55}")
        log.info(f"  BATCH #{run_count}")
        log.info(f"{'#'*55}")

        report = run_batch(config)

        if args.json:
            print(json.dumps(report, indent=2, ensure_ascii=False))
        else:
            print_report(report)

        # Проверить: есть ли что делать
        solvable_count = report["classification"].get("captcha_solvable", 0)
        claimable_count = report["classification"].get("claimable", 0)

        if args.once_only and solvable_count == 0 and claimable_count == 0 and report["claims_success"] == 0:
            log.info("Нечего делать (все мёртвые или неsolvable). Выход (--once-only).")
            break

        if not args.loop:
            break

        interval = args.interval * 60
        log.info(f"Следующий батч через {args.interval} мин...")
        time.sleep(interval)


if __name__ == "__main__":
    raise SystemExit(main())