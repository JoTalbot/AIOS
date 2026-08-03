"""AutonomyCore — главный цикл автономии.

    process_customer(...) — для входящих сообщений покупателей (автоответы).
    process_owner(...)    — для команд владельца в Telegram.

Каждый вызов возвращает Outcome-словарь:
    {"mode": "reply"|"action"|"escalate"|"blocked"|"manual",
     "text": ..., "decision": verdict, "result": ...}
"""
from __future__ import annotations

from typing import Any

from .policy import AutonomyPolicy
from .journal import Journal
from .state import StateStore
from .guardrails import Guardrails
from .planner import Planner
from .executor import Executor
from .escalate import notify_owner, resolve as resolve_approval

_MANUAL_LIKE = {"create_ttn", "send_money", "accept_advance", "create_ad", "boost_ad", "publish"}


class AutonomyCore:
    def __init__(self, root=None):
        self.policy = AutonomyPolicy(root)
        self.journal = Journal()
        self.state = StateStore()
        self.guardrails = Guardrails(self.policy)
        self.planner = Planner(self.policy)
        self.executor = Executor(root)

    # ------------------------------------------------------------------
    def process_customer(self, platform: str, chat: str, text: str,
                         msg_id: str = "", extra: dict | None = None) -> dict:
        """Автономная обработка входящего сообщения покупателя."""
        extra = extra or {}
        if not self.policy.enabled:
            return {"mode": "reply", "text": "", "decision": "DISABLED"}

        # дедупликация + сессия
        sess = self.state.note_message(platform, chat, msg_id or text, text)
        ctx = {
            "customer_trust": sess.trust,
            "aggressive": extra.get("aggressive"),
            "bulk": extra.get("bulk"),
            "rules": extra.get("rules", []),
            "last_offer": sess.last_offer,
        }
        # анти-скам: репутация клиента
        if sess.trust == "risky":
            ctx["rules"] = ctx["rules"] + ["risky_customer"]
        elif sess.trust == "new":
            ctx["rules"] = ctx["rules"] + ["unknown_customer"]

        # Детерминированная страховка цены (независимо от LLM)
        item = extra.get("item")
        low = self.guardrails.low_offer_check(text, item)
        if low is not None:
            # анти-скам: повторные попытки ниже пола снижают репутацию клиента
            sess = self.state.get(platform, chat)
            sess.adjust_reputation(-2)
            self.state.save(sess)
            proposal = {"action": "negotiate_price", "params": {"item": item or "", "offer": None},
                        "risk": "medium", "intent": "negotiate", "platform": platform, "chat": chat}
            outcome = self._route(proposal, low)
            return outcome

        proposal = self.planner.propose(platform, chat, text, owner=False, extra=extra)
        # подхватываем факты из контекста
        if extra.get("item"):
            proposal["params"].setdefault("sku", extra["item"])
            proposal["params"].setdefault("item", extra["item"])
        if extra.get("ad_price") and proposal["params"].get("ad_price") is None:
            proposal["params"]["ad_price"] = extra["ad_price"]

        decision = self.guardrails.evaluate(proposal, ctx)
        outcome = self._route(proposal, decision)
        return outcome

    # ------------------------------------------------------------------
    def process_owner(self, chat: str, text: str) -> dict:
        """Обработка команды владельца в Telegram (обычным языком)."""
        if not self.policy.enabled:
            return {"mode": "reply", "text": "", "decision": "DISABLED"}
        proposal = self.planner.propose("telegram", str(chat), text, owner=True)
        action = proposal.get("action", "")

        # Действия, которые владелец отдаёт напрямую — выполняем (кроме денег/ТТН/публикации)
        if action in ("log_sale", "log_expense", "update_inventory",
                      "query_inventory", "query_finance", "query_price_history",
                      "reply_customer", "deactivate_ad"):
            result = self.executor.execute(proposal)
            self.journal.log(platform="telegram", chat=str(chat), intent="owner",
                             action=action, params=proposal["params"],
                             decision="OWNER_EXEC", result=result.get("status"))
            return {"mode": "action", "text": result.get("message", ""),
                    "decision": "OWNER_EXEC", "result": result, "action": action}

        # Ручные (деньги/ТТН/публикация) — даже владельцу на подтверждение
        if action in _MANUAL_LIKE:
            decision = self.guardrails.evaluate(proposal, {})
            rec = notify_owner(proposal, decision, self.journal)
            return {"mode": "manual", "text": decision.reason, "decision": decision.verdict,
                    "approval_id": rec.get("id")}

        # Всё остальное — просто ответ (или эскалация)
        decision = self.guardrails.evaluate(proposal, {"customer_trust": "owner"})
        return self._route(proposal, decision)

    # ------------------------------------------------------------------
    def _route(self, proposal: dict, decision) -> dict:
        """Разложить решение на исполнение/эскалацию/ответ."""
        action = proposal.get("action", "")
        if decision.allowed:
            result = self.executor.execute(proposal)
            self.journal.log(platform=proposal.get("platform"), chat=proposal.get("chat"),
                             intent=proposal.get("intent"), action=action,
                             params=proposal["params"], decision="ALLOWED",
                             reason=decision.reason, result=result.get("status"))
            return {"mode": "action", "text": result.get("message", ""),
                    "decision": "ALLOWED", "result": result, "action": action}

        if decision.verdict in ("MANUAL", "ESCALATE"):
            rec = notify_owner(proposal, decision, self.journal)
            return {"mode": decision.verdict.lower(), "text": decision.reason,
                    "decision": decision.verdict, "action": action,
                    "approval_id": rec.get("id")}

        if decision.verdict == "BLOCKED":
            self.journal.log(platform=proposal.get("platform"), chat=proposal.get("chat"),
                             action=action, params=proposal["params"],
                             decision="BLOCKED", reason=decision.reason)
            return {"mode": "blocked", "text": decision.reason,
                    "decision": "BLOCKED", "action": action}

        # fallback — эскалация
        rec = notify_owner(proposal, decision, self.journal)
        return {"mode": "escalate", "text": decision.reason, "decision": decision.verdict,
                "approval_id": rec.get("id")}

    # ------------------------------------------------------------------
    def confirm(self, approval_id: str, approve: bool) -> dict:
        """Подтвердить/отклонить ожидающее решение владельца."""
        r = resolve_approval(approval_id, approve, self.journal)
        if r.get("ok") and approve:
            # выполняем одобренное действие
            proposal = {"action": r["action"], "params": r["params"],
                        "platform": r.get("platform", "telegram"), "chat": r.get("chat", "")}
            result = self.executor.execute(proposal)
            return {"ok": True, "result": result, "action": r["action"]}
        return r
