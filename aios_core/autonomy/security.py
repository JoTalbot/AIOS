"""Autonomy Security — защита от промпт-инъекции и валидация выходов LLM.

Три слоя:
  1. detect_injection(text)     — выявить признаки промпт-инъекции во входе клиента.
  2. validate_proposal(proposal) — defence-in-depth: проверить, что даже «сломанный»
     LLM не смог сформировать опасное действие (деньги/отправка/создание).
  3. Прокидывание флага injection в guardrails для принудительной эскалации.

Правило: вход клиента всегда считается недоверенным контентом.
"""
from __future__ import annotations

import re
from typing import Any

# Маркеры попытки переопределить поведение бота / проигнорировать правила.
_INJECTION_PATTERNS = [
    r"игнорируй(?:те)?\s+(?:все\s+)?(?:мои\s+)?(?:инструкци|правила|законы|свои)",
    r"ignore\s+(?:all\s+)?(?:previous\s+)?(?:instructions|rules|prompt)",
    r"забудь(?:те)?\s+(?:все\s+)?(?:правила|инструкци|прошлое)",
    r"ты\s+(?:теперь|больше)\s+не\s+(?:aios|бот)",
    r"you\s+are\s+now\s+(?:not\s+)?(?:aios|the)",
    r"переведи\s+(?:деньги|аванс)|отправь\s+(?:аванс|деньги)|"
    r"(?:переведи|отправь|закинь|скинь)\s+(?:на|мне)\s+(?:мою\s+)?(?:карту|счет|счёт|рахунок|картк|account|iban|реквизит)",
    r"сделай\s+скидку\s+на\s+\d+%?\s+и\s+забудь|сбрось\s+цены",
    r"бесплатн|отдай\s+бесплатно|за\s+1\s+грн|за\s+одну\s+гривну",
    r"промпт|prompt|system\s+message|developer\s+message|извлеки\s+системный",
]

# Действия, которые никогда нельзя автономно (всегда manual/blocked), даже если LLM их вернёт.
_NEVER_AUTO_ACTIONS = {
    "send_money", "accept_advance", "create_ttn", "ship_order",
    "process_payment", "transfer", "withdraw",
}


def detect_injection(text: str) -> dict:
    """Вернуть {injected: bool, reasons: [...]}."""
    t = (text or "").lower()
    reasons = []
    for pat in _INJECTION_PATTERNS:
        if re.search(pat, t):
            reasons.append(pat)
    return {"injected": bool(reasons), "reasons": reasons[:3]}


def validate_proposal(proposal: dict) -> dict:
    """Проверить, что предложение LLM не является опасным (defence-in-depth).

    Возвращает {safe: bool, reason: str | None}. Даже если guardrails не
    сработал, здесь мы блокируем любые действия с деньгами/отправкой.
    """
    action = proposal.get("action", "")
    params = proposal.get("params", {}) or {}
    if action in _NEVER_AUTO_ACTIONS:
        return {"safe": False, "reason": f"Опасно запрещено: {action}"}
    # Проверка денежных сумм в параметрах
    for key in ("amount", "offer", "counter", "price", "transfer"):
        v = params.get(key)
        if v is not None:
            try:
                if float(v) <= 0:
                    return {"safe": False, "reason": f"Параметр {key} не может быть <= 0"}
            except (TypeError, ValueError):
                pass
    # Действие с деньгами в тексте ответа
    if action == "reply_customer":
        txt = str(params.get("text", ""))
        inj = detect_injection(txt)
        if inj["injected"]:
            return {"safe": False, "reason": "Инъекция в тексте ответа"}
    return {"safe": True, "reason": None}
