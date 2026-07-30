#!/usr/bin/env python3
"""faucet_claimer.py — Playwright-based claim с решением hCaptcha.

Интегрируется в faucet_collector.py для captcha_solvable кранов.
Поддерживает:
  - Решение hCaptcha через Capsolver/2Captcha API
  - Инъекцию токена в страницу
  - LNURL-withdraw: извлечение lnurl URI для сканирования кошельком
  - Скриншоты до/после для отладки
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

SKILL_DIR = Path(os.environ.get("OCTOPUS_ME_SKILL_DIR") or Path(__file__).resolve().parents[1])
CONFIG = SKILL_DIR / "config"
DATA = SKILL_DIR / "data"

UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
SCREENSHOT_DIR = DATA / "screenshots"

log = logging.getLogger("faucet_claimer")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def claim_with_captcha(
    faucet: Dict[str, Any],
    config: Dict[str, Any],
    captcha_solver,  # CaptchaSolver instance
    screenshot: bool = True,
) -> Dict[str, Any]:
    """Полный цикл клейма крана с капчей.

    Args:
        faucet: запись из каталога (url, captcha_sitekey, mechanism, etc.)
        config: faucet_config (lightning_address, captcha settings)
        captcha_solver: экземпляр CaptchaSolver
        screenshot: сохранять скриншоты

    Returns:
        Dict с результатом клейма.
    """
    url = faucet.get("url", "")
    sitekey = faucet.get("captcha_sitekey", "")
    faucet_id = faucet.get("id", "unknown")
    ln_address = config.get("lightning_address", "")
    faucet_name = faucet.get("name", faucet_id)

    result = {
        "faucet_id": faucet_id,
        "faucet_name": faucet_name,
        "url": url,
        "ts": utc_now(),
        "status": "started",
        "captcha_solved": False,
        "sats_claimed": 0,
        "cost_usd": 0,
        "detail": "",
        "screenshots": [],
    }

    if not sitekey:
        result["status"] = "no_sitekey"
        result["detail"] = "captcha_sitekey не указан в каталоге"
        return result

    if not ln_address:
        result["status"] = "no_lightning_address"
        result["detail"] = "lightning_address не задан в конфиге"
        return result

    log.info(f"[{faucet_id}] Starting claim: {url}")

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        result["status"] = "no_playwright"
        result["detail"] = "playwright не установлен на сервере"
        return result

    with sync_playwright() as p:
        browser = None
        try:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(
                user_agent=UA,
                viewport={"width": 1280, "height": 800},
            )

            # --- Шаг 1: Загрузка страницы ---
            log.info(f"[{faucet_id}] Loading page...")
            page.goto(url, wait_until="domcontentloaded", timeout=25000)
            page.wait_for_timeout(3000)  # Дать JS время инициализации

            # Скриншот ДО
            if screenshot:
                SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
                ss_before = str(SCREENSHOT_DIR / f"{faucet_id}_before.png")
                page.screenshot(path=ss_before)
                result["screenshots"].append(ss_before)
                log.info(f"[{faucet_id}] Screenshot: {ss_before}")

            # --- Шаг 2: Заполнить Lightning Address (если есть поле) ---
            _try_fill_lightning_address(page, ln_address)

            # --- Шаг 3: Решить hCaptcha ---
            log.info(f"[{faucet_id}] Solving hCaptcha (sitekey={sitekey[:20]}...)...")
            captcha_result = captcha_solver.solve_hcaptcha(sitekey, url)

            if not captcha_result.get("ok"):
                result["status"] = "captcha_failed"
                result["captcha_solved"] = False
                result["detail"] = f"captcha solve failed: {captcha_result.get('error')} — {captcha_result.get('details', '')}"
                result["captcha_result"] = captcha_result
                return result

            token = captcha_result["token"]
            result["captcha_solved"] = True
            result["cost_usd"] = captcha_result.get("cost_usd", 0)
            result["captcha_provider"] = captcha_result.get("provider", "?")
            log.info(f"[{faucet_id}] Captcha solved by {captcha_result['provider']} in {captcha_result.get('time_s', '?')}s")

            # --- Шаг 4: Инжектировать токен в страницу ---
            _inject_hcaptcha_token(page, token)
            page.wait_for_timeout(1500)

            # --- Шаг 5: Найти и нажать кнопку клейма ---
            clicked = _click_claim_button(page)
            if not clicked:
                result["status"] = "no_claim_button"
                result["detail"] = "Кнопка клейма не найдена на странице"
                # Всё равно пробуем извлечь LNURL (может быть уже виден)
            else:
                log.info(f"[{faucet_id}] Claim button clicked, waiting for result...")
                # Ждём появления результата (LNURL, QR, сообщение об успехе)
                page.wait_for_timeout(5000)

            # --- Шаг 6: Анализ результата ---
            content = page.content()

            # Скриншот ПОСЛЕ
            if screenshot:
                ss_after = str(SCREENSHOT_DIR / f"{faucet_id}_after.png")
                page.screenshot(path=ss_after)
                result["screenshots"].append(ss_after)

            # Поиск LNURL в странице
            lnurl_info = _extract_lnurl(content, page)
            if lnurl_info:
                result.update(lnurl_info)
                result["status"] = "lnurl_extracted"
                result["detail"] = "LNURL-withdraw URI извлечён — открой в Lightning-кошельке"
            else:
                # Проверить на другие индикаторы успеха
                success_info = _check_success_indicators(content)
                if success_info:
                    result.update(success_info)
                    result["status"] = "claim_possible"
                else:
                    result["status"] = "captcha_solved_no_result"
                    result["detail"] = "Капча решена, но результат не обнаружен. Скриншот сохранён."
                    # Сохранить фрагмент HTML для анализа
                    result["html_snippet"] = _extract_relevant_html(content)

            return result

        except Exception as e:
            log.error(f"[{faucet_id}] Error: {e}", exc_info=True)
            result["status"] = "error"
            result["detail"] = str(e)
            return result

        finally:
            if browser:
                browser.close()


def _try_fill_lightning_address(page, ln_address: str) -> bool:
    """Попробовать найти и заполнить поле Lightning Address на странице."""
    # Common selectors for Lightning Address input
    selectors = [
        'input[name*="lightning"]',
        'input[name*="lnaddress"]',
        'input[placeholder*="Lightning"]',
        'input[placeholder*="lightning"]',
        'input[placeholder*="lnurl"]',
        'input[type="email"]',  # Lightning Address looks like email
        'input[placeholder*="@"]',
    ]

    for selector in selectors:
        try:
            el = page.query_selector(selector)
            if el and el.is_visible():
                current_val = el.input_value()
                if not current_val:
                    el.fill(ln_address)
                    log.info(f"Filled Lightning Address in: {selector}")
                    return True
        except Exception:
            pass
    return False


def _inject_hcaptcha_token(page, token: str) -> None:
    """Инжектировать hCaptcha токен в страницу.

    Для invisible hCaptcha нужно:
    1. Установить значение textarea[name="h-captcha-response"]
    2. Вызвать hcaptcha.setResponse() если доступен
    3. Диспатчнуть событие для JS-обработчиков
    """
    try:
        page.evaluate(
            """(token) => {
            // 1. Set textarea value
            var ta = document.querySelector('textarea[name="h-captcha-response"]');
            if (ta) {
                ta.value = token;
                ta.textContent = token;
                // Dispatch change event
                ta.dispatchEvent(new Event('change', {bubbles: true}));
                ta.dispatchEvent(new Event('input', {bubbles: true}));
            }

            // 2. Set iframe textarea if exists
            var iframes = document.querySelectorAll('iframe[src*="hcaptcha"]');
            iframes.forEach(iframe => {
                try {
                    var doc = iframe.contentDocument || iframe.contentWindow.document;
                    var ta2 = doc.querySelector('textarea[name="h-captcha-response"]');
                    if (ta2) ta2.value = token;
                } catch(e) { /* cross-origin, expected */ }
            });

            // 3. Call hcaptcha.setResponse if available
            if (window.hcaptcha) {
                try { window.hcaptcha.setResponse(token); } catch(e) {}
            }

            // 4. Also set in any global callback queues
            if (window._hcaptchaOnLoad) {
                try {
                    window._hcaptchaCallback = window._hcaptchaCallback || function() {};
                    window.hcaptcha = window.hcaptcha || {};
                    window.hcaptcha.getResponse = function() { return token; };
                } catch(e) {}
            }

            return true;
        }""",
            token,
        )
        log.info("hCaptcha token injected into page")
    except Exception as e:
        log.warning(f"Token injection error (non-fatal): {e}")


def _click_claim_button(page) -> bool:
    """Найти и нажать кнопку клейма. Возвращает True если кнопка найдена и нажата."""
    # Ordered list of selectors to try
    button_selectors = [
        'button:has-text("Get Sat")',
        'button:has-text("Get Satoshis")',
        'button:has-text("Claim")',
        'button:has-text("claim")',
        'button:has-text("Send")',
        'button:has-text("Receive")',
        'button:has-text("Withdraw")',
        'button:has-text("Free")',
        'button:has-text("Get")',
        'input[type="submit"]',
        'button[type="submit"]',
        "#claim-button",
        'button.btn-primary',
        'button:not([disabled])',
    ]

    for selector in button_selectors:
        try:
            el = page.query_selector(selector)
            if el and el.is_visible():
                el.click()
                log.info(f"Clicked button: {selector}")
                return True
        except Exception:
            pass

    # Fallback: попробовать первый видимый button
    try:
        buttons = page.query_selector_all("button")
        for btn in buttons:
            if btn.is_visible():
                btn_text = btn.inner_text().strip()
                if btn_text and len(btn_text) < 50:
                    btn.click()
                    log.info(f"Clicked fallback button: '{btn_text}'")
                    return True
    except Exception:
        pass

    return False


def _extract_lnurl(content: str, page) -> Optional[Dict[str, Any]]:
    """Извлечь LNURL-withdraw URI из HTML и/или page URL."""
    lnurl_patterns = [
        r'lnurl[wp]:[a-zA-HJ-NP-Za-km-z1-9]+',
        r'lightning:[a-zA-HJ-NP-Za-km-z1-9]+',
        r'LNURL[WP]:[a-zA-HJ-NP-Za-km-z1-9]+',
    ]

    for pattern in lnurl_patterns:
        matches = re.findall(pattern, content)
        if matches:
            lnurl = matches[0]
            log.info(f"Found LNURL: {lnurl[:60]}...")

            # Попробовать декодировать bech32 LNURL
            decoded = _try_decode_lnurl(lnurl)
            info = {"lnurl_raw": lnurl}
            if decoded:
                info["lnurl_decoded"] = decoded
            return info

    # Проверить URL страницы (иногда редирект на lnurl)
    page_url = page.url
    for pattern in lnurl_patterns:
        m = re.search(pattern, page_url)
        if m:
            lnurl = m.group(0)
            log.info(f"Found LNURL in page URL: {lnurl[:60]}...")
            decoded = _try_decode_lnurl(lnurl)
            info = {"lnurl_raw": lnurl}
            if decoded:
                info["lnurl_decoded"] = decoded
            return info

    # Поиск в data-атрибутах
    try:
        data_attrs = page.evaluate(
            """() => {
            const els = document.querySelectorAll('[data-lnurl], [data-lightning], [data-withdraw]');
            const results = [];
            els.forEach(el => {
                for (const attr of el.attributes) {
                    if (attr.value && (attr.value.includes('lnurl') || attr.value.includes('lightning:'))) {
                        results.push(attr.value);
                    }
                }
            });
            return results;
        }"""
        )
        if data_attrs:
            lnurl = data_attrs[0]
            log.info(f"Found LNURL in data attribute: {lnurl[:60]}...")
            return {"lnurl_raw": lnurl, "source": "data_attribute"}
    except Exception:
        pass

    return None


def _try_decode_lnurl(lnurl: str) -> Optional[Dict[str, Any]]:
    """Декодировать bech32 LNURL-withdraw URI (без внешних зависимостей)."""
    # Убираем префикс
    raw = lnurl
    for prefix in ("lnurlp:", "lnurlw:", "lnurl:", "LIGHTNING:", "lightning:"):
        if raw.lower().startswith(prefix.lower()):
            raw = raw[len(prefix):]
            break

    # Простой bech32 декодер для LNURL
    try:
        charset = "qpzry9x8gf2tvdw0s3jn54khce6mua7l"
        #LNURL использует bech32 encoding
        raw_upper = raw.upper()

        # Check HRP
        if "1" not in raw_upper:
            return None

        hrp, data_part = raw_upper.split("1", 1)
        data_vals = []
        for c in data_part:
            if c in charset:
                data_vals.append(charset.index(c))

        if len(data_vals) < 6:
            return None

        # Remove checksum (last 6 chars)
        payload = data_vals[:-6]

        # Convert 5-bit groups to 8-bit bytes
        bytes_data = _convert_bits(payload, 5, 8, False)

        if bytes_data is None:
            return None

        decoded_str = bytes(bytes_data).decode("utf-8", errors="replace")

        # Try to parse as JSON (LNURL-withdraw response)
        if decoded_str.startswith("{"):
            try:
                info = json.loads(decoded_str)
                return info
            except json.JSONDecodeError:
                pass

        # Try to fetch the decoded URL
        if decoded_str.startswith("http"):
            try:
                import urllib.request
                req = urllib.request.Request(
                    decoded_str,
                    headers={"User-Agent": UA, "Accept": "application/json"},
                )
                with urllib.request.urlopen(req, timeout=10) as resp:
                    resp_data = json.loads(resp.read().decode("utf-8"))
                return {
                    "callback_url": decoded_str,
                    "lnurl_response": resp_data,
                }
            except Exception as e:
                return {"callback_url": decoded_str, "fetch_error": str(e)}

        return {"decoded": decoded_str}

    except Exception as e:
        log.debug(f"LNURL decode error: {e}")
        return None


def _convert_bits(data, from_bits, to_bits, pad=True):
    """Convert between bit groups (bech32 utility)."""
    acc = 0
    bits = 0
    result = []
    maxv = (1 << to_bits) - 1
    for value in data:
        if value < 0 or (value >> from_bits):
            return None
        acc = (acc << from_bits) | value
        bits += from_bits
        while bits >= to_bits:
            bits -= to_bits
            result.append((acc >> bits) & maxv)
    if pad:
        if bits:
            result.append((acc << (to_bits - bits)) & maxv)
    elif bits >= from_bits or ((acc << (to_bits - bits)) & maxv):
        return None
    return result


def _check_success_indicators(content: str) -> Optional[Dict[str, Any]]:
    """Проверить индикаторы успешного клейма в HTML."""
    low = content.lower()

    # Success patterns
    success_patterns = [
        (r"(\d+)\s*sat", "sats_mentioned"),
        (r"payment\s+(?:sent|successful|completed)", "payment_sent"),
        (r"invoice\s+(?:paid|settled)", "invoice_paid"),
        (r"successfully", "success_word"),
        (r"claimed", "claimed_word"),
    ]

    for pattern, key in success_patterns:
        m = re.search(pattern, low)
        if m:
            return {"success_indicator": key, "match": m.group(0)}

    return None


def _extract_relevant_html(content: str) -> str:
    """Извлечь релевантный фрагмент HTML для анализа (до 3000 символов)."""
    # Убрать скрипты и стили для компактности
    cleaned = re.sub(r"<script[^>]*>.*?</script>", "", content, flags=re.DOTALL | re.IGNORECASE)
    cleaned = re.sub(r"<style[^>]*>.*?</style>", "", cleaned, flags=re.DOTALL | re.IGNORECASE)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()

    # Найти фрагмент с ключевыми словами
    keywords = ["claim", "captcha", "sat", "lightning", "lnurl", "error", "success", "button", "form"]
    for kw in keywords:
        idx = cleaned.lower().find(kw)
        if idx >= 0:
            start = max(0, idx - 200)
            end = min(len(cleaned), idx + 800)
            return cleaned[start:end]

    return cleaned[:2000]