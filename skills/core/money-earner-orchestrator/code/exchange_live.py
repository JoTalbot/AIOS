#!/usr/bin/env python3
"""exchange_live.py — живой коннектор к бирже для вектора САМООБЕСПЕЧЕНИЕ.

ОТНОСИТСЯ К РЕАЛЬНЫМ ДЕНЬГАМ. Внимательно:

  * Реальный ордер выставляется ТОЛЬКО при полном consent (см. full_consent / can_trade_live).
    По умолчанию ВСЕ условия закрыты → работает только dry-run/paper.
  * consent gate разделяет два уровня:
      - real_funds_unlocked/exchange_trading_allowed — САНКЦИЯ пользователя (стоячее разрешение);
      - execution_armed + api_keys_present + approved_exchanges — ГОТОВНОСТЬ системы исполнять.
        execution_armed — доп. ручной рычаг; нужен явный «взвод» перед live, чтобы автономные
        агенты (см. ~/agents/13_no_unsupervised_autoloops.txt) НЕ могли торговать реальными деньгами сами.
  * Kill-switch: при суммарном реализованном убытке >= max_loss_usd торговля останавливается
    (kill_switch_tripped=true, персистится в ledger).
  * Ключи ТОЛЬКО read+trade (БЕЗ права вывода). Грузятся из secrets-файла вне репозитория.
    Значения ключей НИКОГДА не логируются и не выводятся (маскируются).
  * ccxt — опциональная, ленивая зависимость: если не установлен → live недоступен,
    paper/dry-run работает. Установка: python3 -m pip install ccxt (когда будут ключи).

Безопасность согласована с инструкциями №08, №09, №13, №33, №34, №46.
"""
from __future__ import annotations

import json
import os
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

SKILL_DIR = Path(os.environ.get("OCTOPUS_ME_SKILL_DIR") or Path(__file__).resolve().parents[1])
CONFIG = SKILL_DIR / "config"
DATA = SKILL_DIR / "data"
CONSENT = CONFIG / "consent.json"
LEDGER = DATA / "earnings_ledger.json"
# Ключи хранятся ВНЕ скилла/репозитория, в существующем secrets-каталоге Octopus.
SECRETS_ENV = Path(os.environ.get("OCTOPUS_EXCHANGE_KEYS") or "/root/agents/-Octopus/secrets/exchange.env")

REQUIRED_KEY_FIELDS = ("exchange", "api_key", "api_secret")


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


def full_consent() -> Dict[str, Any]:
    """Расширенный consent: санкция пользователя + готовность системы + kill-switch параметры."""
    c = load_json(CONSENT, {})
    if not isinstance(c, dict):
        c = {}
    return {
        # санкция пользователя (стоячее разрешение на реальные средства)
        "real_funds_unlocked": bool(c.get("real_funds_unlocked", False)),
        "exchange_trading_allowed": bool(c.get("exchange_trading_allowed", False)),
        # готовность системы исполнять (должны быть все true)
        "approved_exchanges": c.get("approved_exchanges", []) or [],
        "api_keys_present": bool(c.get("api_keys_present", False)),
        "execution_armed": bool(c.get("execution_armed", False)),
        # параметры риска
        "max_loss_usd": float(c.get("max_loss_usd", 0) or 0),
        "target_capital_usdt_min": float(c.get("target_capital_usdt_min", 0) or 0),
        "target_capital_usdt_max": float(c.get("target_capital_usdt_max", 0) or 0),
        "mode": c.get("mode", "paper"),
        "human_command_ref": c.get("human_command_ref", ""),
    }


def live_blockers(consent: Optional[Dict[str, Any]] = None) -> List[str]:
    """Список причин, по которым live торговля ЗАБЛОКИРОВАНА. Пустой список = можно торговать."""
    c = consent or full_consent()
    out: List[str] = []
    if not c["real_funds_unlocked"]:
        out.append("real_funds_unlocked=false (нет санкции пользователя)")
    if not c["exchange_trading_allowed"]:
        out.append("exchange_trading_allowed=false")
    if not c["approved_exchanges"]:
        out.append("approved_exchanges пуст (биржа не выбрана)")
    if not c["api_keys_present"]:
        out.append("api_keys_present=false (ключи не загружены)")
    if not c["execution_armed"]:
        out.append("execution_armed=false (нужен явный взвод перед live)")
    if c["max_loss_usd"] <= 0:
        out.append("max_loss_usd<=0 (kill-switch не задан)")
    if not ccxt_available():
        out.append("ccxt не установлен (python3 -m pip install ccxt)")
    if kill_switch_active():
        out.append("kill_switch_tripped=true (лимит потерь достигнут)")
    return out


def can_trade_live(consent: Optional[Dict[str, Any]] = None) -> bool:
    return not live_blockers(consent)


# ---- ccxt (lazy) ----

def ccxt_available() -> bool:
    try:
        import ccxt  # noqa: F401
        return True
    except Exception:
        return False


def _mask(s: str) -> str:
    if not s:
        return "<empty>"
    if len(s) <= 6:
        return "***"
    return s[:3] + "…" + s[-3:]


def load_credentials() -> Optional[Dict[str, str]]:
    """Читать ключи из secrets-файла. Формат KEY=value, строки с # = комментарии.
    Возвращает dict {exchange, api_key, api_secret, passphrase?}. НИКОГДА не логирует значения.
    Полностью безопасна: любой сбой доступа → None (никаких выбросов)."""
    try:
        if not SECRETS_ENV.exists():
            return None
        text = SECRETS_ENV.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return None
    d: Dict[str, str] = {}
    try:
        for raw in text.splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            d[k.strip().lower()] = v.strip()
    except Exception:
        return None
    if not all(f in d and d[f] for f in REQUIRED_KEY_FIELDS):
        return None
    return d


def credentials_fingerprint(creds: Optional[Dict[str, str]]) -> Dict[str, str]:
    """Маскированный отпечаток — БЕЗ значений, безопасно для логов/отчётов."""
    if not creds:
        return {"present": "false"}
    return {
        "present": "true",
        "exchange": creds.get("exchange", "?"),
        "api_key": _mask(creds.get("api_key", "")),
        "api_secret": "***",
        "passphrase": _mask(creds.get("passphrase", "")) if creds.get("passphrase") else "n/a",
    }


# ---- kill-switch ----

def kill_switch_active(max_loss_usd: Optional[float] = None) -> bool:
    ledger = load_json(LEDGER, {})
    if not isinstance(ledger, dict):
        return False
    live = ledger.get("live") if isinstance(ledger.get("live"), dict) else {}
    if live.get("kill_switch_tripped"):
        return True
    if max_loss_usd is None:
        max_loss_usd = full_consent().get("max_loss_usd", 0)
    realized_loss = float(live.get("realized_loss_usd", 0.0) or 0.0)
    return max_loss_usd > 0 and realized_loss >= max_loss_usd


def _fetch_price(timeout: int = 8) -> Optional[float]:
    """Best-effort цена из публичных источников (для размера ордера). Offline-safe."""
    if os.environ.get("OCTOPUS_ME_OFFLINE") == "1":
        forced = os.environ.get("OCTOPUS_ME_PRICE")
        return float(forced) if forced else None
    forced = os.environ.get("OCTOPUS_ME_PRICE")
    if forced:
        try:
            return float(forced)
        except ValueError:
            pass
    for url in ("https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd",
                "https://www.bitstamp.net/api/v2/ticker/btcusd/"):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "octopus-money-earner/1.0"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = json.loads(resp.read(4096).decode("utf-8", errors="replace"))
            p = data.get("bitcoin", {}).get("usd") if isinstance(data, dict) else None
            if p is None and isinstance(data, dict):
                p = data.get("last")
            if isinstance(p, (int, float)) and p > 0:
                return float(p)
        except Exception:
            continue
    return None


def record_live_trade(ledger_path: Path, side: str, symbol: str, amount_base: float,
                      price: float, quote_usd: float, realized_pnl_usd: float,
                      order_id: str, max_loss_usd: float, dry_run: bool) -> Dict[str, Any]:
    """Персист live-сделку в ledger и обновить kill-switch. Безопасно (только локальный файл)."""
    ledger = load_json(ledger_path, {})
    if not isinstance(ledger, dict):
        ledger = {}
    live = ledger.setdefault("live", {})
    live.setdefault("trades", [])
    live["trades"].append({
        "ts": utc_now(), "side": side, "symbol": symbol, "amount_base": round(amount_base, 8),
        "price": round(price, 2), "quote_usd": round(quote_usd, 2),
        "realized_pnl_usd": round(realized_pnl_usd, 2), "order_id": order_id, "dry_run": dry_run,
    })
    if side == "sell" and realized_pnl_usd < 0:
        live["realized_loss_usd"] = round(float(live.get("realized_loss_usd", 0.0)) + realized_pnl_usd, 2)
    if max_loss_usd > 0 and float(live.get("realized_loss_usd", 0.0)) <= -abs(max_loss_usd):
        live["kill_switch_tripped"] = True
        live["kill_switch_reason"] = f"realized_loss {live['realized_loss_usd']} <= -{max_loss_usd}"
    live["updated"] = utc_now()
    ledger["updated"] = utc_now()
    save_json(ledger_path, ledger)
    return live


def live_trade_step(symbol: str = "BTC/USDT", quote_usdt: float = 0.0,
                    force_dry_run: bool = False) -> Dict[str, Any]:
    """Один bounded live-шаг. Реальный ордер — только при can_trade_live(); иначе dry-run/paper.
    side = пересечение SMA из текущей paper-позиции в ledger (buy если вне позиции и есть кэш, sell если в позиции).
    """
    consent = full_consent()
    blockers = live_blockers(consent)
    creds = load_credentials()
    price = _fetch_price()
    ledger = load_json(LEDGER, {})
    if not isinstance(ledger, dict):
        ledger = {}
    paper = ledger.get("paper") if isinstance(ledger.get("paper"), dict) else {}
    position = paper.get("position") if isinstance(paper.get("position"), dict) else {}
    in_position = float(position.get("btc", 0.0) or 0.0) > 0
    side = "sell" if in_position else "buy"

    base = {
        "ts": utc_now(), "symbol": symbol, "side": side, "price_usd": price,
        "creds": credentials_fingerprint(creds),
        "can_trade_live": False, "dry_run": True, "order_id": None,
        "amount_base": 0.0, "quote_usd": 0.0, "realized_pnl_usd": 0.0,
        "blockers": blockers,
    }

    # Если нельзя торговать реально — dry-run (симуляция), реальный ордер не отправляется.
    if force_dry_run or blockers or creds is None or price is None:
        base["reason"] = "dry_run_or_blocked"
        return base

    # === РЕАЛЬНЫЙ ОРДЕР (только если все условия выполнены) ===
    try:
        import ccxt
    except Exception as e:  # на всякий случай (can_trade_live уже проверил)
        base["blockers"].append(f"ccxt import error: {type(e).__name__}")
        base["reason"] = "ccxt_unavailable"
        return base

    ex_name = creds["exchange"].lower()
    ex_cls = getattr(ccxt, ex_name, None)
    if ex_cls is None:
        base["blockers"].append(f"unknown ccxt exchange: {ex_name}")
        base["reason"] = "unknown_exchange"
        return base
    params: Dict[str, Any] = {"apiKey": creds["api_key"], "secret": creds["api_secret"], "enableRateLimit": True}
    if creds.get("passphrase"):
        params["password"] = creds["passphrase"]
    exchange = ex_cls(params)

    qty_quote = quote_usdt if quote_usdt > 0 else consent["target_capital_usdt_min"]
    if qty_quote <= 0:
        base["blockers"].append("quote_usdt<=0 and target_capital_usdt_min<=0")
        base["reason"] = "no_size"
        return base
    amount_base = qty_quote / price

    order_id = "ERR"
    realized = 0.0
    try:
        if side == "buy":
            order = exchange.create_market_buy_order(symbol, amount_base)
        else:
            order = exchange.create_market_sell_order(symbol, float(position.get("btc", 0.0) or 0.0))
        order_id = str(order.get("id") or "OK")
        base["amount_base"] = amount_base if side == "buy" else float(position.get("btc", 0.0) or 0.0)
        base["quote_usd"] = qty_quote if side == "buy" else base["amount_base"] * price
        if side == "sell":
            entry = float(position.get("entry_price", price) or price)
            realized = base["amount_base"] * (price - entry)
    except Exception as e:
        base["blockers"].append(f"order_error: {type(e).__name__}: {str(e)[:120]}")
        base["reason"] = "order_failed"
        return base

    live = record_live_trade(LEDGER, side, symbol, base["amount_base"], price, base["quote_usd"],
                             realized, order_id, consent["max_loss_usd"], dry_run=False)
    base.update({
        "can_trade_live": True, "dry_run": False, "order_id": order_id,
        "realized_pnl_usd": round(realized, 2), "reason": "live_order_placed",
        "realized_loss_usd": live.get("realized_loss_usd", 0.0),
        "kill_switch_tripped": bool(live.get("kill_switch_tripped")),
    })
    return base
