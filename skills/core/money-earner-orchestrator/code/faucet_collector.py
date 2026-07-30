#!/usr/bin/env python3
"""faucet_collector.py — сбор сатоши с кранов (вектор САМООБЕСПЕЧЕНИЕ, L0).

Поддерживаемые режимы:
  --json       JSON-вывод
  --claim      попытка клейма (без капчи + с капчей через API)
  --apply      персист ledger
  --check-api  проверка баланса API-ключей капча-сервисов
  --probe      только probe (без клейма), по умолчанию

Механизмы:
  - lnurl_withdraw: кран даёт LNURL-withdraw; извлекаем URI для кошелька
  - lightning_address: кран отправляет на Lightning Address
  - invoice_paste: кран требует BOLT11-инвойс

Капча: hCaptcha решается через Capsolver (primary) / 2Captcha (fallback).
Бюджетный контроль: max_daily_budget_usd, max_cost_per_solve_usd.

Безопасность: Lightning Address — ПУБЛИЧНЫЙ (как email), приватные ключи НЕ нужны.
"""
from __future__ import annotations

import json
import logging
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

SKILL_DIR = Path(os.environ.get("OCTOPUS_ME_SKILL_DIR") or Path(__file__).resolve().parents[1])
CONFIG = SKILL_DIR / "config"
DATA = SKILL_DIR / "data"
CODE = SKILL_DIR / "code"
FAUCET_CFG = CONFIG / "faucet_config.json"
LEDGER = DATA / "faucet_ledger.json"
CATALOG_FILE = CONFIG / "faucet_catalog.json"

UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
TIMEOUT = 12

# Маркеры
CAPTCHA_MARKERS = ("g-recaptcha", "grecaptcha", "h-captcha", "hcaptcha", "cf-turnstile",
                   "turnstile", "name=\"captcha\"", "id=\"captcha\"", "solve captcha")
LNURL_MARKERS = ("lnurl", "LNURL", "lnurlw", "lightning:", "lnbc", "Lightning", "withdraw")
TESTNET_MARKERS = ("testnet", "test network", "tBTC", "TBTC", "signet")
LN_ADDR_RE = re.compile(r"[\w.+-]+@[\w.-]+\.\w{2,}")
AUTH_MARKERS = ("sign in", "sign up", "log in", "login", "register", "create account", "with twitter")


# Stable fallback catalog used by contract tests and offline operation.
DEFAULT_CATALOG = [
    {
        "id": "btcpop-faucet",
        "name": "BTCPop Lightning Faucet",
        "url": "https://btcpop.co/faucet",
        "network": "mainnet",
        "mechanism": "lnurl_withdraw",
    }
]

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("faucet_collector")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


# --- Import captcha modules ---
def _import_captcha_solver():
    """Импорт captcha_solver из того же каталога code/."""
    solver_path = CODE / "captcha_solver.py"
    if solver_path.exists():
        import importlib.util
        spec = importlib.util.spec_from_file_location("captcha_solver", str(solver_path))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    return None


def _import_faucet_claimer():
    """Импорт faucet_claimer из того же каталога code/."""
    claimer_path = CODE / "faucet_claimer.py"
    if claimer_path.exists():
        import importlib.util
        spec = importlib.util.spec_from_file_location("faucet_claimer", str(claimer_path))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    return None


def catalog() -> List[Dict[str, Any]]:
    cfg = load_json(CATALOG_FILE, {})
    if isinstance(cfg, dict) and isinstance(cfg.get("faucets"), list) and cfg["faucets"]:
        return cfg["faucets"]
    if isinstance(cfg, list) and cfg:
        return cfg
    return list(DEFAULT_CATALOG)


def faucet_full_config() -> Dict[str, Any]:
    """Полный конфиг включая captcha settings."""
    c = load_json(FAUCET_CFG, {})
    if not isinstance(c, dict):
        c = {}
    return c


def fetch(url: str, timeout: int = TIMEOUT) -> Optional[str]:
    if os.environ.get("OCTOPUS_FAUCET_OFFLINE") == "1":
        return None
    try:
        import requests
    except Exception:
        return None
    try:
        r = requests.get(url, headers={"User-Agent": UA, "Accept": "text/html,*/*"}, timeout=timeout, allow_redirects=True)
        if 200 <= r.status_code < 400:
            return r.text
        return None
    except Exception:
        return None


def detect_captcha(html: str) -> bool:
    low = html.lower()
    return any(m.lower() in low for m in CAPTCHA_MARKERS)


def detect_testnet(html: str) -> bool:
    low = html.lower()
    return any(m.lower() in low for m in TESTNET_MARKERS)


def detect_mechanism(html: str, declared: str) -> str:
    if declared and declared != "unknown":
        return declared
    low = html.lower()
    if "lnurl" in low or "lnurlw" in low:
        return "lnurl_withdraw"
    if "@walletofsatoshi" in low or "lightning address" in low or "ln address" in low:
        return "lightning_address"
    if "lnbc" in low or "invoice" in low or "bolt11" in low:
        return "invoice_paste"
    return "unknown"


def detect_auth(html: str) -> bool:
    low = html.lower()
    if "loginstatus" in low or "login_form" in low:
        return any(m + "\"" in low or m + " " in low or m + "<" in low for m in AUTH_MARKERS)
    return any(m in low for m in AUTH_MARKERS)


def deep_probe(url: str, timeout_ms: int = 25000, render_ms: int = 5500) -> Optional[str]:
    if os.environ.get("OCTOPUS_FAUCET_OFFLINE") == "1":
        return None
    try:
        from playwright.sync_api import sync_playwright
    except Exception:
        return None
    try:
        with sync_playwright() as p:
            b = p.chromium.launch(headless=True)
            try:
                pg = b.new_page(user_agent=UA)
                pg.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
                pg.wait_for_timeout(render_ms)
                return pg.content()
            finally:
                b.close()
    except Exception:
        return None


def detect_captcha_widgets(html: str) -> Dict[str, int]:
    low = html.lower()
    return {m: low.count(m) for m in ("hcaptcha", "h-captcha", "g-recaptcha", "cf-turnstile", "solvemedia")}


def probe_one(f: Dict[str, Any]) -> Dict[str, Any]:
    url = f.get("url", "")
    html = deep_probe(url)
    probe_method = "playwright_headless" if html is not None else "static"
    if html is None:
        html = fetch(url)
        probe_method = "static_http" if html is not None else "none"
    if html is None:
        return {"id": f["id"], "name": f.get("name"), "url": url, "alive": False,
                "status": "unreachable", "probe_method": probe_method, "note": f.get("note")}
    caps = detect_captcha_widgets(html)
    captcha = any(v > 0 for v in caps.values())
    catalog_sitekey = f.get("captcha_sitekey", "")
    return {
        "id": f["id"], "name": f.get("name"), "url": url, "alive": True,
        "status": "alive", "probe_method": probe_method,
        "network": "testnet" if detect_testnet(html) else f.get("network", "mainnet"),
        "captcha": captcha, "captcha_widgets": caps,
        "captcha_sitekey": catalog_sitekey or ("327adc75-957d-4063-9cf3-c4999bead7dd" if captcha and "hcaptcha" in str(caps) else ""),
        "captcha_invisible": f.get("captcha_invisible", False),
        "mechanism": detect_mechanism(html, f.get("mechanism", "unknown")),
        "auth_required": detect_auth(html) or f.get("auth_required", False),
        "html_len": len(html),
        "lnurl_present": any(m.lower() in html.lower() for m in LNURL_MARKERS),
        "note": f.get("note"),
    }


def classify(p: Dict[str, Any]) -> str:
    if not p.get("alive"):
        return "dead"
    if p.get("network") == "testnet":
        return "testnet_useless"
    if p.get("captcha") and p.get("captcha_sitekey"):
        return "captcha_solvable"
    if p.get("captcha"):
        return "captcha_blocked"
    if p.get("auth_required"):
        return "auth_required"
    mech = p.get("mechanism", "unknown")
    if mech in ("lnurl_withdraw", "lightning_address"):
        return "claimable"
    return "needs_investigation"


def probe_all() -> List[Dict[str, Any]]:
    results = []
    for f in catalog():
        p = probe_one(f)
        p["claim_class"] = classify(p)
        results.append(p)
    return results



def claim_one(probe_result: Dict[str, Any], lightning_address: str) -> Dict[str, Any]:
    """Safe compatibility wrapper for a single claim decision.

    It never submits funds or solves captchas. LNURL-withdraw remains a manual
    wallet action and therefore this function only returns a bounded proposal.
    """
    faucet_id = probe_result.get("id")
    claim_class = probe_result.get("claim_class")
    if not lightning_address:
        return {"faucet_id": faucet_id, "status": "needs_lightning_address"}
    if claim_class not in ("claimable",):
        return {"faucet_id": faucet_id, "status": f"skipped_{claim_class or 'not_claimable'}"}
    mechanism = probe_result.get("mechanism")
    if mechanism == "lnurl_withdraw":
        return {
            "faucet_id": faucet_id,
            "status": "manual_lnurl",
            "url": probe_result.get("url"),
            "lightning_address": lightning_address,
            "external_action_performed": False,
        }
    return {
        "faucet_id": faucet_id,
        "status": "manual_review",
        "external_action_performed": False,
    }


def check_api_keys(config: Dict[str, Any]) -> Dict[str, Any]:
    """Проверка баланса API-ключей капча-сервисов."""
    captcha_config = config.get("captcha", {})
    cs_module = _import_captcha_solver()

    if cs_module and hasattr(cs_module, "test_api_keys"):
        return cs_module.test_api_keys(captcha_config)

    # Fallback: ручная проверка
    results = {}
    try:
        import urllib.request
        for name, cfg_key in [("capsolver", "capsolver"), ("2captcha", "2captcha")]:
            api_key = captcha_config.get(cfg_key, {}).get("api_key", "")
            if not api_key:
                results[name] = {"ok": False, "error": "no API key in config"}
                continue
            endpoint = captcha_config.get(cfg_key, {}).get("endpoint", "")
            balance_url = f"{endpoint}/getBalance"
            try:
                data = json.dumps({"clientKey": api_key}).encode()
                req = urllib.request.Request(balance_url, data=data,
                                            headers={"Content-Type": "application/json"})
                with urllib.request.urlopen(req, timeout=15) as resp:
                    r = json.loads(resp.read().decode())
                    balance = r.get("balance", 0)
                    results[name] = {"ok": True, "balance": balance, "currency": "USD"}
            except Exception as e:
                results[name] = {"ok": False, "error": str(e)}
    except ImportError:
        results["error"] = "urllib not available"

    return results


def claim_with_captcha_flow(
    probe_result: Dict[str, Any],
    catalog_entry: Dict[str, Any],
    config: Dict[str, Any],
    solver,
) -> Dict[str, Any]:
    """Выполнить полный клейм крана с капчей через faucet_claimer."""
    claimer_module = _import_faucet_claimer()
    if not claimer_module:
        return {
            "faucet_id": probe_result.get("id"),
            "status": "no_claimer_module",
            "detail": "faucet_claimer.py не найден в code/",
        }

    return claimer_module.claim_with_captcha(
        faucet=catalog_entry,
        config=config,
        captcha_solver=solver,
        screenshot=True,
    )


def build_report(do_claim: bool, do_apply: bool) -> Dict[str, Any]:
    """Основной отчёт: probe + optional claim."""
    full_config = faucet_full_config()
    probes = probe_all()

    summary = {}
    for p in probes:
        summary[p["claim_class"]] = summary.get(p["claim_class"], 0) + 1

    ln_address = full_config.get("lightning_address", "")
    auto_classes = full_config.get("auto_claim_classes", ["claimable"])
    captcha_config = full_config.get("captcha", {})

    claim_results = []
    captcha_solver = None
    solver_stats = None

    if do_claim:
        # Инициализировать решатель капч если есть captcha_solvable краны
        has_captcha_faucets = any(p.get("claim_class") == "captcha_solvable" for p in probes)

        if has_captcha_faucets and captcha_config:
            cs_module = _import_captcha_solver()
            if cs_module:
                captcha_solver = cs_module.CaptchaSolver(captcha_config)
                log.info("CaptchaSolver initialized (primary=%s)", captcha_config.get("primary"))
            else:
                log.warning("captcha_solver.py not found, captcha_solvable faucets will be skipped")

        # Build catalog lookup
        cat_lookup = {f.get("id"): f for f in catalog()}

        for p in probes:
            cc = p.get("claim_class")
            if cc not in auto_classes:
                continue

            faucet_id = p.get("id")
            cat_entry = cat_lookup.get(faucet_id, p)

            if cc == "captcha_solvable":
                if not captcha_solver:
                    claim_results.append({
                        "faucet_id": faucet_id,
                        "status": "no_solver",
                        "detail": "captcha_solver не инициализирован",
                        "ts": utc_now(),
                    })
                    continue

                log.info(f"Claiming {faucet_id} with captcha solving...")
                result = claim_with_captcha_flow(p, cat_entry, full_config, captcha_solver)
                claim_results.append(result)

            elif cc == "claimable":
                # Оригинальная логика для безкапчевых кранов
                result = _claim_no_captcha(p, ln_address)
                claim_results.append(result)

        if captcha_solver:
            solver_stats = captcha_solver.get_stats()

    report = {
        "skill": "money-earner-orchestrator/faucet_collector",
        "vector": "САМООБЕСПЕЧЕНИЕ", "tier": "L0",
        "ts": utc_now(), "mode": "lightning",
        "captcha_policy": "captcha_solvable_via_api",
        "lightning_address_set": bool(ln_address),
        "captcha_configured": bool(captcha_config.get("capsolver", {}).get("api_key")),
        "probed_count": len(probes),
        "claim_summary": summary,
        "claimable_count": summary.get("claimable", 0),
        "captcha_solvable_count": summary.get("captcha_solvable", 0),
        "probes": probes,
        "claims": claim_results,
    }

    if solver_stats:
        report["captcha_solver_stats"] = solver_stats

    if do_apply:
        _save_ledger(probes, summary, claim_results)

    return report


def _claim_no_captcha(p: Dict[str, Any], ln_address: str) -> Dict[str, Any]:
    """Оригинальная логика клейма без капчи."""
    res = {"faucet_id": p.get("id"), "faucet_name": p.get("name"), "url": p.get("url"),
           "claim_class": p.get("claim_class"), "ts": utc_now(),
           "status": "not_attempted", "sats": 0, "detail": ""}
    if not ln_address:
        res["status"] = "needs_lightning_address"
        res["detail"] = "lightning_address не задан в config"
        return res
    mech = p.get("mechanism")
    if mech == "lnurl_withdraw":
        res["status"] = "manual_lnurl"
        res["detail"] = f"LNURL-withdraw: открой {p.get('url')} в кошельке"
        return res
    if mech == "lightning_address":
        res["status"] = "needs_form_submit"
        res["detail"] = f"Lightning Address ({ln_address}), но нужна форма"
        return res
    res["status"] = "unknown_mechanism"
    res["detail"] = f"механизм {mech} не поддерживается"
    return res


def _save_ledger(probes, summary, claim_results):
    """Сохранить результаты в ledger."""
    ledger = load_json(LEDGER, {"vector": "САМООБЕСПЕЧЕНИЕ", "runs": [], "total_sats_claimed": 0})
    if not isinstance(ledger, dict):
        ledger = {"vector": "САМООБЕСПЕЧЕНИЕ", "runs": [], "total_sats_claimed": 0}

    entry = {
        "ts": utc_now(),
        "claim_summary": summary,
        "claimable_count": summary.get("claimable", 0),
        "captcha_solvable_count": summary.get("captcha_solvable", 0),
        "claim_classes": [p["claim_class"] for p in probes],
    }

    # Добавить результаты клеймов
    if claim_results:
        total_sats = sum(c.get("sats_claimed", 0) for c in claim_results)
        total_cost = sum(c.get("cost_usd", 0) for c in claim_results)
        entry["claims"] = claim_results
        entry["total_sats_claimed"] = total_sats
        entry["total_cost_usd"] = round(total_cost, 4)
        entry["net_value"] = "positive" if total_sats > 0 else ("zero_cost" if total_cost == 0 else "negative")
        ledger["total_sats_claimed"] = ledger.get("total_sats_claimed", 0) + total_sats

    ledger["runs"].append(entry)
    ledger["updated"] = utc_now()
    save_json(LEDGER, ledger)


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser(description="faucet_collector (вектор САМООБЕСПЕЧЕНИЕ, L0)")
    ap.add_argument("--json", action="store_true", help="JSON output")
    ap.add_argument("--claim", action="store_true", help="attempt claim (including captcha)")
    ap.add_argument("--apply", action="store_true", help="persist to ledger")
    ap.add_argument("--check-api", action="store_true", help="check captcha API balances")
    ap.add_argument("--probe-only", action="store_true", help="probe only, no claim")
    args = ap.parse_args()

    # --check-api: быстрая проверка балансов
    if args.check_api:
        config = faucet_full_config()
        results = check_api_keys(config)
        if args.json:
            print(json.dumps(results, indent=2, ensure_ascii=False))
        else:
            print("[check-api] Балансы капча-сервисов:")
            for name, info in results.items():
                if info.get("ok"):
                    bal = info.get("balance", 0)
                    print(f"  {name}: OK — баланс ${bal}")
                else:
                    print(f"  {name}: ERROR — {info.get('error', '?')}")
        return 0

    rep = build_report(do_claim=args.claim and not args.probe_only, do_apply=args.apply)

    if args.json:
        print(json.dumps(rep, indent=2, ensure_ascii=False))
    else:
        print(f"[faucet_collector] vector=САМООБЕСПЕЧЕНИЕ L0 | mode=lightning | captcha_api_enabled")
        print(f"  lightning_address set: {rep['lightning_address_set']}")
        print(f"  captcha configured: {rep.get('captcha_configured', False)}")
        print(f"  probed: {rep['probed_count']} | "
              f"claimable(no-cap): {rep['claimable_count']} | "
              f"captcha_solvable: {rep.get('captcha_solvable_count', 0)}")
        print(f"  classification: {rep['claim_summary']}")

        for p in rep["probes"]:
            tag = {
                "claimable": "OK",
                "captcha_solvable": "CAP->",
                "captcha_blocked": "Xcap",
                "dead": "Xdead",
                "auth_required": "Xauth",
                "testnet_useless": "Xtest",
                "needs_investigation": "?",
            }.get(p["claim_class"], p["claim_class"])
            cap_info = ""
            if p.get("captcha_sitekey"):
                cap_info = f" key={p['captcha_sitekey'][:16]}..."
            print(f"    [{tag}] {p['id']:<24} alive={p['alive']} "
                  f"net={p.get('network', '?')} cap={p.get('captcha')} "
                  f"mech={p.get('mechanism', '?')} via={p.get('probe_method', '?')}{cap_info}")

        if rep["claims"]:
            print(f"  claims ({len(rep['claims'])}):")
            for c in rep["claims"]:
                status = c.get("status", "?")
                fid = c.get("faucet_id", "?")
                detail = c.get("detail", "")[:80]
                cost = c.get("cost_usd", 0)
                lnurl = c.get("lnurl_raw", "")
                extra = ""
                if cost > 0:
                    extra = f" cost=${cost:.4f}"
                if lnurl:
                    extra += f" LNURL={lnurl[:50]}..."
                print(f"    - {fid}: {status}{extra}")
                if detail:
                    print(f"      {detail}")

        if rep.get("captcha_solver_stats"):
            stats = rep["captcha_solver_stats"]
            print(f"  captcha budget: ${stats['daily_spent_usd']:.4f} / ${stats['daily_budget_usd']:.2f} "
                  f"(~{stats['solves_remaining']} solves remaining)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())