#!/usr/bin/env python3
"""
AIOS OLX Autoreply — автономные ответы покупателям в OLX-чате.

Использует единый контур автономии (aios_core.autonomy.AutonomyCore):
  вход покупателя -> intent -> LLM-предложение -> guardrails -> исполнение.

Режимы (data/olx_autoreply.json):
  enabled    : bool  — общий вкл/выкл
  auto_send  : bool  — если true, разрешённые ответы шлются в OLX-чат авто;
                       если false — предлагаемый ответ отправляется владельцу на подтверждение.
  max_replies_per_run : int — лимит автоответов за один цикл.

Команды в боте: «включи автоответ OLX» / «выключи автоответ OLX».
"""
from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

CFG = ROOT / "data" / "olx_autoreply.json"
PY = "/opt/aios/.venv/bin/python"


def _env(key: str) -> str:
    import os
    v = os.environ.get(key, "")
    if v:
        return v
    p = ROOT / ".env"
    if p.exists():
        try:
            for line in p.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line.startswith(key + "="):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
        except Exception:
            pass
    return ""


def _load_cfg() -> dict:
    default = {"enabled": False, "auto_send": True, "max_replies_per_run": 3}
    try:
        cfg = json.loads(CFG.read_text(encoding="utf-8"))
        cfg = {**default, **cfg}
        return cfg
    except Exception:
        return default


def _save_cfg(cfg: dict) -> None:
    CFG.parent.mkdir(parents=True, exist_ok=True)
    CFG.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")


def _run_ac(args: list[str], timeout: int = 170) -> dict:
    """Запустить run_account_control.py для OLX-чата (браузер → xvfb)."""
    helper = str(ROOT / "run_account_control.py")
    cmd = ["xvfb-run", "-a", "-s", "-screen 0 1440x900x24", PY, helper] + args
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd=str(ROOT))
    except subprocess.TimeoutExpired:
        return {"status": "error", "error": "timeout (браузер занят)"}
    except Exception as e:
        return {"status": "error", "error": str(e)[:200]}
    out = (r.stdout or "").strip()
    if not out:
        return {"status": "error", "error": (r.stderr or "пустой ответ")[-400:]}
    try:
        start = out.find("{")
        return json.loads(out[start:]) if start >= 0 else {"status": "error", "error": out[-400:]}
    except Exception:
        return {"status": "error", "error": out[-400:]}


def _tg(token: str, chat_id: int, text: str, reply_markup: dict | None = None) -> None:
    import urllib.request
    import html as _html
    payload = {"chat_id": chat_id, "text": _html.escape(text)[:3800],
               "parse_mode": "HTML", "disable_web_page_preview": True}
    if reply_markup:
        payload["reply_markup"] = reply_markup
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60):
        pass


def _sale_context(contact: str) -> str:
    """Контекст сделки из pending_sales для данного клиента (чтобы LLM не забывал).

    Возвращает строку с деталями сделки (товар/цена/доставка/ФИО/телефон) или "".
    """
    try:
        p = ROOT / "data" / "pending_sales.json"
        if not p.exists():
            return ""
        import json as _json
        sales = _json.loads(p.read_text(encoding="utf-8"))
        # последняя сделка этого клиента со статусом pending
        for s in reversed(sales):
            if s.get("chat") == contact and s.get("status") == "pending":
                parts = []
                if s.get("item"):
                    parts.append(f"товар: {s['item']}")
                if s.get("amount"):
                    parts.append(f"ціна: {s['amount']} грн")
                if s.get("delivery"):
                    parts.append(f"доставка: {s['delivery']}")
                if s.get("recipient"):
                    parts.append(f"отримувач: {s['recipient']}")
                if s.get("customer_phone"):
                    parts.append(f"телефон: {s['customer_phone']}")
                return "; ".join(parts)
    except Exception:
        pass
    return ""


def _detect_item(text: str) -> str | None:
    """Сопоставить текст сообщения с товарами из склада (для ценового пола)."""
    try:
        import run_inventory
        items = run_inventory._load()
    except Exception:
        items = []
    t = (text or "").lower()
    for it in items:
        name = (it.get("name") or "").strip()
        if not name:
            continue
        if name.lower() in t or t in name.lower():
            return name
    # также ищем по известным полам
    try:
        import json
        floors = json.loads((ROOT / "data" / "price_floors.json").read_text(encoding="utf-8"))
        for key in floors.get("items", {}):
            if key in t:
                return key
    except Exception:
        pass
    return None


def get_olx_threads() -> list[dict]:
    """Список переписок OLX-чата: [{contact, text, unread}]."""
    res = _run_ac(["olx", "chat", "list", "--limit", "20"], timeout=170)
    threads = res.get("threads", []) or []
    return threads


def read_olx(contact: str) -> dict:
    return _run_ac(["olx", "chat", "read", contact, "--limit", "15"], timeout=170)


def reply_olx(contact: str, text: str, retries: int = 3, wait: int = 20) -> dict:
    """Отправить ответ в OLX-чат с ретраями при блокировке CloudFront.

    OLX временно блокирует (CloudFront) при частых обращениях — повторяем
    до `retries` раз с паузой `wait` сек. Возвращает последний результат.
    """
    last = {"status": "error", "error": "не выполнено"}
    for attempt in range(1, retries + 1):
        res = _run_ac(["olx", "chat", "reply", contact, text, "--confirm"], timeout=170)
        status = res.get("status", "")
        err = str(res.get("error", "") or "")
        # успех или не найден контакт — дальше не повторяем
        if status == "ok" or status == "sent":
            return res
        if "не найдена" in err or "not found" in err.lower():
            return res
        # блокировка/временная ошибка — повтор
        print(f"  [OLX-reply] попытка {attempt}/{retries} для {contact} не удалась: {err[:80]}", flush=True)
        last = res
        if attempt < retries:
            time.sleep(wait)
    return last


_PENDING = ROOT / "data" / "olx_pending_replies.json"


def _save_pending_reply(contact: str, text: str) -> str:
    """Сохранить неотправленный ответ; возвращает короткий id для кнопки."""
    try:
        data = {}
        if _PENDING.exists():
            data = json.loads(_PENDING.read_text(encoding="utf-8"))
        rid = f"r{int(time.time()*1000)}"
        data[rid] = {"contact": contact, "text": text, "ts": time.time()}
        # держим максимум 50
        if len(data) > 50:
            oldest = sorted(data, key=lambda k: data[k].get("ts", 0))[:len(data)-50]
            for k in oldest:
                data.pop(k, None)
        _PENDING.parent.mkdir(parents=True, exist_ok=True)
        _PENDING.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        return rid
    except Exception:
        return ""


def _get_pending_reply(rid: str) -> dict | None:
    """Получить неотправленный ответ по id и удалить его."""
    try:
        if not _PENDING.exists():
            return None
        data = json.loads(_PENDING.read_text(encoding="utf-8"))
        item = data.pop(rid, None)
        _PENDING.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        return item
    except Exception:
        return None


def main() -> int:
    from aios_core.autonomy import AutonomyCore

    token = _env("TELEGRAM_BOT_TOKEN") or _env("AIOS_TELEGRAM_TOKEN")
    chat_id = _env("TELEGRAM_CHAT_ID")
    cfg = _load_cfg()
    if not cfg.get("enabled"):
        print("Автоответ OLX выключен")
        return 0

    core = AutonomyCore()
    if not core.policy.enabled:
        print("Автономия выключена в data/autonomy_policy.json")
        return 0

    threads = get_olx_threads()
    if not threads:
        print("OLX-чат: переписок нет")
        return 0

    max_r = int(cfg.get("max_replies_per_run", 3))
    replied = 0
    actions_summary = []

    for th in threads[:20]:
        if replied >= max_r:
            break
        contact = (th.get("name") or "").strip()
        last = (th.get("text") or "").strip()
        if not contact or not last:
            continue

        # прочитать переписку, чтобы понять контекст
        conv = read_olx(contact)
        msgs = conv.get("messages", []) or []

        # последнее сообщение НЕ от нас — надо ответить
        last_theirs = None
        for m in msgs:
            if not m.get("mine"):
                last_theirs = m.get("text", "")
                break
        if not last_theirs:
            continue

        # дедупликация: если последнее сообщение клиента уже обработано — пропуск.
        # Используем текст сообщения КЛИЕНТА, а не превью (превью может быть нашим ответом).
        sess = core.state.get("olx", contact)
        if sess.last_seen_msg == f"{contact}:{last_theirs}":
            continue  # уже отвечали на это сообщение клиента

        detected = _detect_item(last_theirs)
        # Контекст сделки из pending_sales (товар/цена/доставка/данные клиента),
        # чтобы LLM НЕ забывал уже согласованные детали.
        sale_ctx = _sale_context(contact)
        outcome = core.process_customer(
            "olx", contact, last_theirs, msg_id=f"{contact}:{last}",
            extra={"item": detected, "ad_price": None, "history": msgs,
                   "sale_context": sale_ctx})

        # действие — автоответ
        if outcome.get("mode") == "action" and outcome.get("text"):
            reply_text = outcome["text"]
            auto = cfg.get("auto_send", True)
            if auto:
                res = reply_olx(contact, reply_text)
                if res.get("status") in ("ok", "sent"):
                    replied += 1
                    actions_summary.append(f"✅ {contact}: {reply_text[:60]}")
                    # пометить, что на это сообщение клиента уже ответили
                    # (на случай, если ручная отправка/другой процесс обошёл note_message)
                    try:
                        s2 = core.state.get("olx", contact)
                        s2.data["last_seen_msg"] = f"{contact}:{last_theirs}"
                        core.state.save(s2)
                    except Exception:
                        pass
                else:
                    # не отправилось после ретраев — сохранить и уведомить с кнопкой
                    rid = _save_pending_reply(contact, reply_text)
                    _tg(token, int(chat_id),
                        f"⚠️ <b>Автоответ OLX не отправился {contact}:</b> {res.get('error','?')}\n\n"
                        f"<b>Сгенерированный ответ:</b>\n{reply_text[:500]}\n\n"
                        f"Нажмите кнопку, чтобы отправить.",
                        reply_markup={"inline_keyboard": [[
                            {"text": "📤 Отправить ответ", "callback_data": f"olx_send_{rid}"}]]})
            else:
                _tg(token, int(chat_id),
                    f"💬 <b>Предлагаемый ответ для {contact}:</b>\n{reply_text[:600]}\n\n"
                    f"Отправить: «ответь в олх: {contact} | текст» или включи auto_send.")
        elif outcome.get("mode") in ("escalate", "manual", "blocked"):
            # эскалация уже уведомила владельца
            if outcome.get("text"):
                actions_summary.append(f"🔎 {contact}: {outcome['decision']} — {outcome['text'][:60]}")

    if actions_summary:
        _tg(token, int(chat_id), "📊 <b>Цикл автоответа OLX</b>\n" + "\n".join(actions_summary[:10]))

    # алерты аномалий (не чаще 1 раза в час)
    _maybe_anomaly_alert(token, chat_id)
    # алерт при недоступности LLM
    _maybe_llm_down_alert(token, chat_id)
    return 0


def _maybe_llm_down_alert(token: str, chat_id: int) -> None:
    """Уведомить владельца, если LLM-провайдеры недоступны (не чаще 1/час)."""
    try:
        from aios_core.autonomy import Journal
        j = Journal()
        # последние решения — есть ли признак недоступности LLM
        state_p = ROOT / "data" / "autonomy_llm_alert.json"
        try:
            last = float(state_p.read_text().strip())
        except Exception:
            last = 0.0
        if time.time() - last < 3600:
            return
        # проверим балансер напрямую
        from aios_core.llm_balancer import LLMBalancer
        b = LLMBalancer()
        s = b.status()
        any_avail = any(pd.get("keys_available", 0) > 0 for pd in s.get("providers", {}).values())
        if not any_avail:
            _tg(token, int(chat_id),
                "⚠️ <b>LLM недоступен:</b> все провайдеры исчерпаны/недоступны. "
                "Автономия будет отвечать с задержкой или эскалировать. Проверьте ключи.")
            state_p.write_text(str(time.time()))
    except Exception:
        pass


def _maybe_anomaly_alert(token: str, chat_id: int) -> None:
    """Отправить владельцу уведомление об аномалиях (не чаще 1/час)."""
    try:
        from aios_core.autonomy.report import anomalies
        state_p = ROOT / "data" / "autonomy_alert_state.json"
        try:
            last = float(state_p.read_text().strip())
        except Exception:
            last = 0.0
        if time.time() - last < 3600:
            return
        anom = anomalies()
        if anom:
            lines = ["🚨 <b>Аномалии автономии</b>"]
            for a in anom[:5]:
                lines.append(f"• {a.get('note', a.get('type'))}")
            _tg(token, int(chat_id), "\n".join(lines))
            state_p.write_text(str(time.time()))
    except Exception:
        pass


if __name__ == "__main__":
    sys.exit(main())
