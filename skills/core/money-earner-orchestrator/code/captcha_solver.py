from captcha_paid_gate import paid_captcha_slot
#!/usr/bin/env python3
"""captcha_solver.py — решение hCaptcha через Capsolver (primary) и 2Captcha (fallback).

Использует HTTP API напрямую через urllib (zero dependencies).
Бюджетный контроль: max_cost_per_solve, max_daily_budget.
"""

import json
import os
import time
import logging
import urllib.request
import urllib.error

log = logging.getLogger("captcha_solver")

# Стоимость решения hCaptcha (ориентировочно USD)
HCAPTCHA_COST_USD = 0.002  # ~$0.002 за hCaptcha на обоих сервисах


if __name__ == '__main__' and os.environ.get('OCTOPUS_EXTERNAL_EFFECT_LOCKED') != '1':
    raise SystemExit('paid CAPTCHA executor requires with_external_effect_lock.sh')

class CaptchaSolveError(Exception):
    """Ошибка решения капчи."""
    def __init__(self, provider: str, reason: str, details: str = ""):
        self.provider = provider
        self.reason = reason
        self.details = details
        super().__init__(f"[{provider}] {reason}: {details}")


class CaptchaSolver:
    """Решатель hCaptcha с fallback и бюджетным контролем."""

    def __init__(self, captcha_config: dict):
        self.primary = captcha_config.get("primary", "capsolver")
        self.max_daily = captcha_config.get("max_daily_budget_usd", 0.50)
        self.max_per_solve = captcha_config.get("max_cost_per_solve_usd", 0.003)
        self.providers = {
            "capsolver": {
                "api_key": captcha_config.get("capsolver", {}).get("api_key", ""),
                "create_url": "https://api.capsolver.com/createTask",
                "result_url": "https://api.capsolver.com/getTaskResult",
            },
            "2captcha": {
                "api_key": captcha_config.get("2captcha", {}).get("api_key", ""),
                "create_url": "https://api.2captcha.com/createTask",
                "result_url": "https://api.2captcha.com/getTaskResult",
            },
        }
        self.daily_spent = 0.0
        self.solves_today = 0
        self._log = []

    def _api_request(self, url: str, payload: dict, provider: str) -> dict:
        """POST JSON request к API капча-сервиса."""
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace") if e.fp else ""
            raise CaptchaSolveError(provider, f"HTTP {e.code}", body[:500])
        except urllib.error.URLError as e:
            raise CaptchaSolveError(provider, "network error", str(e.reason))
        except Exception as e:
            raise CaptchaSolveError(provider, "unknown error", str(e))

    def _check_budget(self) -> bool:
        """Проверка дневного бюджета. Возвращает True если можно решать."""
        if self.daily_spent >= self.max_daily:
            log.warning(
                f"Бюджет исчерпан: ${self.daily_spent:.4f} / ${self.max_daily:.2f}"
            )
            return False
        return True

    def _solve_capsolver(self, sitekey: str, page_url: str) -> str:
        """Решение hCaptcha через Capsolver API."""
        p = self.providers["capsolver"]
        if not p["api_key"]:
            raise CaptchaSolveError("capsolver", "no API key configured")

        # Создание задачи
        create_payload = {
            "clientKey": p["api_key"],
            "task": {
                "type": "HCaptchaTaskProxyLess",
                "websiteURL": page_url,
                "websiteKey": sitekey,
            },
        }
        log.info("[capsolver] Creating task...")
        resp = self._api_request(p["create_url"], create_payload, "capsolver")

        task_id = resp.get("taskId")
        if not task_id:
            err_code = resp.get("errorId")
            err_desc = resp.get("errorDescription", "")
            raise CaptchaSolveError("capsolver", f"createTask failed (errId={err_code})", err_desc)

        log.info(f"[capsolver] Task {task_id[:16]}... created, polling...")

        # Ожидание результата (макс ~60 секунд)
        for attempt in range(30):
            time.sleep(2)
            result_payload = {"clientKey": p["api_key"], "taskId": task_id}
            resp = self._api_request(p["result_url"], result_payload, "capsolver")
            status = resp.get("status", "")

            if status == "ready":
                token = resp.get("solution", {}).get("gRecaptchaResponse", "")
                if token:
                    elapsed = (attempt + 1) * 2
                    log.info(f"[capsolver] Solved in ~{elapsed}s (token len={len(token)})")
                    return token
                raise CaptchaSolveError("capsolver", "no token in solution", json.dumps(resp))

            if status == "failed":
                err_desc = resp.get("errorDescription", "unknown failure")
                raise CaptchaSolveError("capsolver", "task failed", err_desc)

            # status == "processing" — продолжаем ожидание
            log.debug(f"[capsolver] Still processing... (attempt {attempt + 1}/30)")

        raise CaptchaSolveError("capsolver", "timeout", "30 polling attempts x 2s = 60s")

    def _solve_2captcha(self, sitekey: str, page_url: str) -> str:
        """Решение hCaptcha через 2Captcha API."""
        p = self.providers["2captcha"]
        if not p["api_key"]:
            raise CaptchaSolveError("2captcha", "no API key configured")

        # Создание задачи
        create_payload = {
            "clientKey": p["api_key"],
            "task": {
                "type": "HCaptchaTaskProxyless",
                "websiteURL": page_url,
                "websiteKey": sitekey,
            },
        }
        log.info("[2captcha] Creating task...")
        resp = self._api_request(p["create_url"], create_payload, "2captcha")

        if resp.get("errorId", 0) != 0:
            err_desc = resp.get("errorDescription", "unknown error")
            raise CaptchaSolveError("2captcha", "createTask failed", err_desc)

        task_id = resp.get("taskId")
        if not task_id:
            raise CaptchaSolveError("2captcha", "no taskId in response", json.dumps(resp))

        log.info(f"[2captcha] Task {task_id[:16]}... created, polling...")

        # Ожидание результата (макс ~120 секунд)
        for attempt in range(40):
            time.sleep(3)
            result_payload = {"clientKey": p["api_key"], "taskId": task_id}
            resp = self._api_request(p["result_url"], result_payload, "2captcha")
            status = resp.get("status", "")

            if status == "ready":
                token = resp.get("solution", {}).get("gRecaptchaResponse", "")
                if token:
                    elapsed = (attempt + 1) * 3
                    log.info(f"[2captcha] Solved in ~{elapsed}s (token len={len(token)})")
                    return token
                raise CaptchaSolveError("2captcha", "no token in solution", json.dumps(resp))

            if resp.get("errorId", 0) != 0:
                err_desc = resp.get("errorDescription", "unknown error")
                raise CaptchaSolveError("2captcha", "task failed", err_desc)

            log.debug(f"[2captcha] Still processing... (attempt {attempt + 1}/40)")

        raise CaptchaSolveError("2captcha", "timeout", "40 polling attempts x 3s = 120s")

    def solve_hcaptcha(self, sitekey: str, page_url: str) -> dict:
        """Решить hCaptcha. Возвращает dict с результатом.

        Returns:
            {"ok": True, "token": "...", "provider": "capsolver", "cost_usd": 0.002, "time_s": 12}
            {"ok": False, "error": "...", "provider": "...", "details": "..."}
        """
        if not self._check_budget():
            return {
                "ok": False,
                "error": "daily_budget_exhausted",
                "details": f"spent ${self.daily_spent:.4f} of ${self.max_daily:.2f}",
            }

        if not sitekey:
            return {"ok": False, "error": "no_sitekey", "details": "sitekey is empty"}

        t0 = time.time()
        order = [self.primary]
        fallback = "2captcha" if self.primary == "capsolver" else "capsolver"
        if fallback not in order:
            order.append(fallback)

        last_error = None
        for provider_name in order:
            try:
                log.info(f"Attempting {provider_name} (sitekey={sitekey[:20]}...)")
                if provider_name == "capsolver":
                    token = self._solve_capsolver(sitekey, page_url)
                else:
                    token = self._solve_2captcha(sitekey, page_url)

                elapsed = time.time() - t0
                self.daily_spent += self.max_per_solve
                self.solves_today += 1

                result = {
                    "ok": True,
                    "token": token,
                    "provider": provider_name,
                    "cost_usd": self.max_per_solve,
                    "time_s": round(elapsed, 1),
                    "daily_spent": round(self.daily_spent, 4),
                    "solves_today": self.solves_today,
                }
                self._log.append(result)
                return result

            except CaptchaSolveError as e:
                last_error = e
                log.warning(f"{provider_name} failed: {e}")
                continue
            except Exception as e:
                last_error = CaptchaSolveError(provider_name, "unexpected", str(e))
                log.warning(f"{provider_name} unexpected error: {e}")
                continue

        elapsed = time.time() - t0
        return {
            "ok": False,
            "error": "all_providers_failed",
            "provider": self.primary,
            "details": str(last_error) if last_error else "unknown",
            "time_s": round(elapsed, 1),
        }

    def get_stats(self) -> dict:
        """Статистика решения капч."""
        return {
            "daily_spent_usd": round(self.daily_spent, 4),
            "daily_budget_usd": self.max_daily,
            "budget_remaining": round(self.max_daily - self.daily_spent, 4),
            "solves_today": self.solves_today,
            "solves_remaining": int((self.max_daily - self.daily_spent) / self.max_per_solve),
        }


def test_api_keys(captcha_config: dict) -> dict:
    """Быстрая проверка API-ключей (balance check).

    Returns:
        {"capsolver": {"ok": True/False, "balance": ...}, "2captcha": {"ok": True/False, "balance": ...}}
    """
    results = {}

    # Capsolver balance check
    cap_key = captcha_config.get("capsolver", {}).get("api_key", "")
    if cap_key:
        try:
            data = json.dumps({"clientKey": cap_key}).encode()
            req = urllib.request.Request(
                "https://api.capsolver.com/getBalance",
                data=data,
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                r = json.loads(resp.read().decode())
                results["capsolver"] = {"ok": True, "balance": r.get("balance", 0)}
        except Exception as e:
            results["capsolver"] = {"ok": False, "error": str(e)}
    else:
        results["capsolver"] = {"ok": False, "error": "no API key"}

    # 2Captcha balance check
    cap2_key = captcha_config.get("2captcha", {}).get("api_key", "")
    if cap2_key:
        try:
            data = json.dumps({"clientKey": cap2_key}).encode()
            req = urllib.request.Request(
                "https://api.2captcha.com/getBalance",
                data=data,
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                r = json.loads(resp.read().decode())
                results["2captcha"] = {"ok": True, "balance": r.get("balance", 0)}
        except Exception as e:
            results["2captcha"] = {"ok": False, "error": str(e)}
    else:
        results["2captcha"] = {"ok": False, "error": "no API key"}

    return results
