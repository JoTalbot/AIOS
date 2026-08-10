"""Reaction engine Phone Brain (этап 4): декларативные правила на события телефона.

Наблюдает уведомления Companion и применяет правила из ``phone_reactions/``:

.. code-block:: yaml

    id: bank_income_alert
    title: "Поступление на карту"
    match:
      package: [ua.privatbank.ap24, ua.com.abank]
      text_regex: "(поповн|зарах|зачисл)"
    action: {type: telegram, template: "💰 {label}: {text}"}
    autonomy: alert_only            # alert_only | draft | auto
    cooldown_seconds: 300

Уровни автономии:
* ``alert_only`` — только Telegram-алерт владельцу (значение по умолчанию);
* ``draft``      — задача ставится в очередь БЕЗ confirm → останавливается в
  статусе need_confirm (черновик на одобрение владельца);
* ``auto``       — задача ставится с confirm=true (выполнится сразу).

Приватность: regex и шаблоны работают только с МАСКИРОВАННЫМ текстом
(та же схема, что у run_android_notification_collector.py) — OTP-коды и
номера карт покидают сервер только в виде ••••.
"""
from __future__ import annotations

import hashlib
import html
import json
import re
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Callable

from aios_core.phone_brain.common import iso, parse_iso, read_json, utc_now, write_json

APP_LABELS = {
    "com.whatsapp": "WhatsApp",
    "ua.com.abank": "A-Bank",
    "ua.privatbank.ap24": "Privat24",
    "ua.com.uklontaxi": "Uklon",
    "ua.com.uklon.uklondriver": "Uklon Driver",
    "com.iMe.android": "iMe Messenger",
    "com.eway": "EasyWay",
    "ua.slando": "OLX",
}

ACTION_TYPES = {"telegram", "enqueue", "event", "llm_enqueue"}
MAX_SEEN = 500


def _mask(value: str) -> str:
    """Маскирование OTP/карт — идентично notification collector."""
    text = str(value or "")
    text = re.sub(r"\b\d{4,8}\b", "••••", text)
    text = re.sub(r"\b(?:\d[ -]?){12,19}\b", "••••", text)
    return text[:300]


def _event_id(item: dict) -> str:
    raw = "|".join(str(item.get(k) or "") for k in ("package", "title", "text", "posted_at"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]


class RuleError(Exception):
    """Некорректное правило (пропускается при загрузке)."""


def _validate_rule(data: Any, path: Path) -> dict:
    if not isinstance(data, dict):
        raise RuleError("корень должен быть объектом")
    rule_id = str(data.get("id") or "").strip()
    if not rule_id:
        raise RuleError("нет id")
    match = data.get("match") or {}
    if not isinstance(match, dict):
        raise RuleError("match должен быть объектом")
    packages = [str(p) for p in (match.get("package") or [])][:10]
    if not packages and not match.get("text_regex") and not match.get("title_regex"):
        raise RuleError("нужен package или regex")
    action = data.get("action") or {}
    if action.get("type") not in ACTION_TYPES:
        raise RuleError(f"action.type должен быть одним из {sorted(ACTION_TYPES)}")
    if action.get("type") in ("enqueue", "llm_enqueue"):
        job = action.get("job") or {}
        if not isinstance(job, dict) or not job.get("kind"):
            raise RuleError(f"{action['type']}: нужен job.kind")
    autonomy = str(data.get("autonomy") or "alert_only")
    if autonomy not in ("alert_only", "draft", "auto"):
        raise RuleError("autonomy: alert_only | draft | auto")
    for field in ("text_regex", "title_regex"):
        if match.get(field):
            re.compile(str(match[field]))  # ранняя проверка синтаксиса
    return {"id": rule_id, "title": str(data.get("title") or rule_id)[:120],
            "match": {"package": packages,
                      "text_regex": str(match.get("text_regex") or ""),
                      "title_regex": str(match.get("title_regex") or "")},
            "action": action, "autonomy": autonomy,
            "cooldown_seconds": max(0, int(data.get("cooldown_seconds") or 0)),
            "file": path.name, "enabled": bool(data.get("enabled", True))}


class ReactionEngine:
    """Загружает правила, оценивает уведомления, выполняет действия."""

    def __init__(self, root: Path | str, gateway: Any, store: Any = None,
                 events: Any = None, rules_dir: Path | str | None = None,
                 state_path: Path | str | None = None,
                 env: dict | None = None,
                 sender: Callable[[str], dict] | None = None,
                 chat: Callable | None = None,
                 now_fn: Callable[[], Any] = utc_now):
        self.root = Path(root)
        self.gateway = gateway
        self.store = store
        self.events = events
        self.rules_dir = Path(rules_dir) if rules_dir else self.root / "phone_reactions"
        self.state_path = (Path(state_path) if state_path
                           else self.root / "data" / "android_gateway" / "reactions_state.json")
        self.env = env or {}
        self._sender = sender
        self._chat = chat  # в тестах подменяется; в проде — LLMBalancer (лениво)
        self._now = now_fn
        self._rules: list[dict] | None = None
        self.load_errors: list[dict] = []

    # ------------------------------------------------------------- loading

    def _ensure_loaded(self) -> None:
        if self._rules is not None:
            return
        self._rules = []
        self.load_errors = []
        if not self.rules_dir.exists():
            return
        import yaml  # type: ignore
        for path in sorted(self.rules_dir.iterdir()):
            if path.suffix.lower() not in (".yaml", ".yml", ".json") or not path.is_file():
                continue
            try:
                raw = path.read_text(encoding="utf-8")
                data = yaml.safe_load(raw) if path.suffix.lower() in (".yaml", ".yml") else json.loads(raw)
                self._rules.append(_validate_rule(data, path))
            except Exception as exc:
                self.load_errors.append({"file": path.name, "error": str(exc)[:160]})

    def reload(self) -> int:
        self._rules = None
        self._ensure_loaded()
        return len(self._rules)

    def list_rules(self) -> list[dict]:
        self._ensure_loaded()
        items = [{k: rule[k] for k in ("id", "title", "autonomy", "cooldown_seconds", "file", "enabled")}
                 | {"packages": rule["match"]["package"]}
                 for rule in self._rules]
        for error in self.load_errors:
            items.append({"id": "", "title": "⚠️ битое правило", "autonomy": "", "enabled": False,
                          "cooldown_seconds": 0, "file": error["file"], "error": error["error"],
                          "packages": []})
        return items

    # -------------------------------------------------------------- state

    def _state(self) -> dict:
        state = read_json(self.state_path, {})
        return {"seen": list(state.get("seen") or [])[-MAX_SEEN:],
                "fired": dict(state.get("fired") or {})}

    def _save_state(self, state: dict) -> None:
        write_json(self.state_path, {"seen": state["seen"][-MAX_SEEN:], "fired": state["fired"]})

    def state_summary(self) -> dict:
        state = self._state()
        return {"seen": len(state["seen"]), "fired": len(state["fired"])}

    # ------------------------------------------------------------- matching

    def _matches(self, rule: dict, item: dict, masked_text: str, masked_title: str) -> bool:
        # Игнорировать сообщения от контакта/источника "AIOS" (системные боты)
        raw_title = str(item.get("title") or item.get("contact") or masked_title or "").lower()
        if "aios" in raw_title:
            return False

        packages = rule["match"]["package"]
        if packages and str(item.get("package") or "") not in packages:
            return False
        text_re = rule["match"].get("text_regex") or ""
        if text_re and not re.search(text_re, masked_text, flags=re.IGNORECASE):
            return False
        title_re = rule["match"].get("title_regex") or ""
        if title_re and not re.search(title_re, masked_title, flags=re.IGNORECASE):
            return False
        return True

    def _on_cooldown(self, state: dict, rule: dict) -> bool:
        if not rule["cooldown_seconds"]:
            return False
        last = parse_iso(state["fired"].get(rule["id"]))
        if not last:
            return False
        return (self._now() - last).total_seconds() < rule["cooldown_seconds"]

    # ------------------------------------------------------------- actions

    def _telegram(self, text: str) -> dict:
        if self._sender is not None:
            result = self._sender(text)
            return result if isinstance(result, dict) else {"status": "ok"}
        token = str(self.env.get("TELEGRAM_BOT_TOKEN") or "")
        chat_id = str(self.env.get("TELEGRAM_CHAT_ID") or "")
        if not token or not chat_id:
            return {"status": "error", "error": "нет TELEGRAM_BOT_TOKEN/TELEGRAM_CHAT_ID"}
        payload = {"chat_id": chat_id, "text": text[:900], "parse_mode": "HTML",
                   "disable_web_page_preview": True}
        request = urllib.request.Request(
            f"https://api.telegram.org/bot{token}/sendMessage",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(request, timeout=15) as response:
                ok = bool(json.loads(response.read().decode("utf-8")).get("ok"))
            return {"status": "ok" if ok else "error", "error": "" if ok else "telegram api"}
        except (urllib.error.URLError, OSError, ValueError) as exc:
            return {"status": "error", "error": str(exc)[:160]}

    @staticmethod
    def _ctx(item: dict, masked_title: str, masked_text: str) -> dict:
        package = str(item.get("package") or "")
        return {"label": html.escape(APP_LABELS.get(package, package), quote=False),
                "package": html.escape(package, quote=False),
                "title": html.escape(masked_title, quote=False),
                "text": html.escape(masked_text, quote=False)}

    @staticmethod
    def _render(value: Any, ctx: dict) -> Any:
        if isinstance(value, str):
            try:
                return value.format_map(ctx)
            except (KeyError, ValueError):
                return value
        if isinstance(value, dict):
            return {key: ReactionEngine._render(item, ctx) for key, item in value.items()}
        if isinstance(value, list):
            return [ReactionEngine._render(item, ctx) for item in value]
        return value

    def _fire(self, state: dict, rule: dict, item: dict,
              masked_title: str, masked_text: str) -> dict:
        action = rule["action"]
        ctx = self._ctx(item, masked_title, masked_text)
        kind = action["type"]
        self._event("reaction_fired", {"rule": rule["id"], "type": kind,
                                       "package": str(item.get("package") or "")[:60]})
        if kind == "llm_enqueue":
            return self._fire_llm_enqueue(state, rule, item, masked_title, masked_text)
        if kind == "telegram":
            text = str(self._render(str(action.get("template") or "{label}: {text}"), ctx))
            result = self._telegram(text)
            return {"rule": rule["id"], "type": "telegram", "ok": result.get("status") == "ok",
                    "error": result.get("error") or ""}
        if kind == "enqueue":
            if self.store is None:
                return {"rule": rule["id"], "type": "enqueue", "ok": False, "error": "store недоступен"}
            job_spec = self._render(action.get("job") or {}, ctx)
            payload = job_spec.get("payload") if isinstance(job_spec.get("payload"), dict) else {}
            if rule["autonomy"] == "auto":
                payload["confirm"] = True
            job = self.store.enqueue(str(job_spec.get("kind") or ""), payload,
                                     priority=int(job_spec.get("priority") or 60),
                                     dedup_key=(f"react/{rule['id']}/"
                                                + _event_id(item)) if job_spec.get("dedup", True) else None)
            ok = job.get("status") != "error"
            return {"rule": rule["id"], "type": "enqueue", "ok": ok, "job_id": job.get("id"),
                    "autonomy": rule["autonomy"], "error": job.get("error") or ""}
        # event
        self._event(str(action.get("name") or "reaction_event"),
                    {"rule": rule["id"], "package": str(item.get("package") or "")[:60]})
        return {"rule": rule["id"], "type": "event", "ok": True}

    # ------------------------------------------------------------ llm draft

    def _contact_style(self, contact: str) -> str:
        """Персональный стиль общения с конкретным контактом (data/contact_styles.json)."""
        try:
            d = json.loads((self.root / "data" / "contact_styles.json").read_text(encoding="utf-8"))
            s = str(d.get(str(contact or "").strip()) or "")
            return (" Стиль для этого контакта: " + s + ".") if s else ""
        except Exception:
            return ""

    def _style_hint(self) -> str:
        """Память стиля: решения владельца по прошлым черновикам."""
        try:
            data = json.loads((self.root / "data" / "draft_feedback.json").read_text(encoding="utf-8"))
        except Exception:
            return ""
        if len(data) < 3:
            return ""
        canc = sum(1 for d in data if d.get("decision") == "cancelled")
        conf = sum(1 for d in data if d.get("decision") == "confirmed")
        if canc > conf:
            return (" Стиль: владелец отменял часть черновиков — пиши короче и конкретнее, "
                    "без лишних реверансов, сразу по сути.")
        if conf >= 3:
            return " Стиль: владелец подтверждает черновики — держи текущий тон и структуру."
        return ""

    def _guardrail(self, draft: str) -> list:
        """Безопасность черновика: обещания цены против склада, личные данные."""
        import re as _re
        warns = []
        try:
            inv = json.loads((self.root / "data" / "inventory.json").read_text(encoding="utf-8"))
        except Exception:
            inv = []
        low = (draft or "").lower()
        for m in _re.finditer(r"(\d[\d\s]{2,6})\s*(?:грн|uah)", draft or "", _re.IGNORECASE):
            try:
                val = float(m.group(1).replace(" ", ""))
            except ValueError:
                continue
            for it in inv if isinstance(inv, list) else []:
                name = str(it.get("name") or "")
                words = [w for w in _re.split(r"[^a-zа-яєіїґ0-9]+", name.lower()) if len(w) >= 4]
                if words and all(w in low for w in words[:2]):
                    price = float(it.get("price") or 0)
                    if price and val < price * 0.85:
                        warns.append(f"⚠️ черновик обещает {val:.0f} грн, "
                                     f"а в складе «{name}» — {price:.0f} грн: проверьте цену")
        if _re.search(r"\b(?:\d[ -]?){12,19}\b", draft or ""):
            warns.append("⚠️ в тексте похоже на номер карты")
        if _re.search(r"\+?\d{10,13}", (draft or "").replace(" ", "").replace("-", "")):
            warns.append("⚠️ в тексте похоже на номер телефона")
        return warns[:3]

    def _llm_draft(self, prompt: str) -> dict:
        """Генерирует черновик через LLMBalancer (в тестах — через подменённый chat)."""
        prompt = prompt + self._style_hint()
        chat = self._chat
        if chat is None:
            try:
                from aios_core.phone_brain.planner import _balancer_chat
                chat = _balancer_chat()
            except Exception as exc:
                return {"status": "error", "error": str(exc)[:160]}
        try:
            text = str(chat([{"role": "user", "content": prompt}],
                            max_tokens=220, temperature=0.4, task_type="reply") or "")
            text = text.strip().strip('"').strip()
        except Exception as exc:
            return {"status": "error", "error": str(exc)[:160]}
        if not text:
            return {"status": "error", "error": "пустой ответ LLM"}
        return {"status": "ok", "draft": text[:500]}

    def _fire_llm_enqueue(self, state: dict, rule: dict, item: dict,
                          masked_title: str, masked_text: str) -> dict:
        """LLM-черновик → задача в очередь (+Telegram-уведомление с id для одобрения)."""
        action = rule["action"]
        if self.store is None:
            return {"rule": rule["id"], "type": "llm_enqueue", "ok": False,
                    "error": "store недоступен"}
        ctx = self._ctx(item, masked_title, masked_text)
        prompt = str(self._render(str(action.get("prompt") or "{text}"), ctx))
        prompt = prompt + self._contact_style(masked_title)
        drafted = self._llm_draft(prompt)
        if drafted.get("status") != "ok":
            self._event("llm_draft_failed", {"rule": rule["id"],
                                             "error": str(drafted.get("error"))[:120]})
            return {"rule": rule["id"], "type": "llm_enqueue", "ok": False,
                    "error": str(drafted.get("error"))[:160]}
        warns = self._guardrail(drafted["draft"])
        draft_ctx = dict(ctx)
        draft_ctx["draft"] = drafted["draft"]  # для payload телефона — без HTML-экранирования
        job_spec = action.get("job") or {}
        payload = self._render(job_spec.get("payload") or {}, draft_ctx)
        if not isinstance(payload, dict):
            payload = {}
        if rule["autonomy"] == "auto":
            payload["confirm"] = True
        if warns:
            payload["warnings"] = warns
        job = self.store.enqueue(str(job_spec.get("kind") or ""), payload,
                                 priority=int(job_spec.get("priority") or 60),
                                 dedup_key=(f"react/{rule['id']}/" + _event_id(item))
                                 if job_spec.get("dedup", True) else None)
        if job.get("status") == "error":
            return {"rule": rule["id"], "type": "llm_enqueue", "ok": False,
                    "error": job.get("error")}
        self._event("llm_draft_ready", {"rule": rule["id"], "job_id": job.get("id"),
                                        "autonomy": rule["autonomy"]})
        if action.get("notify", True):
            note = (f"✉️ <b>Черновик #{job.get('id')}</b> ({ctx['label']})\n"
                    f"{html.escape(drafted['draft'][:400], quote=False)}\n\n"
                    + ("\n".join(html.escape(w, quote=False) for w in warns) + "\n" if warns else "")
                    + ("🟢 Автономия auto — выполнится сам."
                       if rule["autonomy"] == "auto" else
                       f"Подтвердить отправку: <code>confirm {job.get('id')}</code>"))
            self._telegram(note)
        return {"rule": rule["id"], "type": "llm_enqueue", "ok": True,
                "job_id": job.get("id"), "autonomy": rule["autonomy"]}

    def _event(self, event_type: str, data: dict) -> None:
        if self.events is not None:
            try:
                self.events.append(event_type, data)
            except Exception:
                pass

    # ---------------------------------------------------------------- tick

    def tick(self) -> dict:
        """Один цикл: взять уведомления → применить правила → действия."""
        self._ensure_loaded()
        try:
            result = self.gateway.notifications(limit=50)
        except Exception as exc:
            return {"status": "error", "error": str(exc)[:160], "checked": 0, "matched": 0}
        if result.get("status") != "ok":
            return {"status": result.get("status", "error"), "checked": 0, "matched": 0}
        state = self._state()
        seen = set(state["seen"])
        outcomes: list[dict] = []
        checked = 0
        for item in result.get("notifications") or []:
            if not isinstance(item, dict):
                continue
            package = str(item.get("package") or "")
            if package not in APP_LABELS:
                continue
            event_id = _event_id(item)
            if event_id in seen:
                continue
            seen.add(event_id)
            state["seen"].append(event_id)
            checked += 1
            masked_text = _mask(str(item.get("text") or ""))
            masked_title = _mask(str(item.get("title") or ""))
            for rule in self._rules:
                if not rule["enabled"] or self._on_cooldown(state, rule):
                    continue
                if not self._matches(rule, item, masked_text, masked_title):
                    continue
                state["fired"][rule["id"]] = iso(self._now())
                outcomes.append(self._fire(state, rule, item, masked_title, masked_text))
        self._save_state(state)
        return {"status": "ok", "checked": checked, "matched": len([o for o in outcomes if o["ok"]]),
                "actions": outcomes}
