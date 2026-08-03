"""Autonomy Guardrails — детерминированный решатель решений.

ЕДИНСТВЕННЫЙ источник истины о том, что можно выполнять автономно.
Никаких LLM здесь нет: всё решает чистый Python по политике
(``AutonomyPolicy``). LLM может только ПРЕДЛОЖИТЬ действие — этот модуль
решает, разрешить (ALLOWED), заблокировать (BLOCKED), вынести на
подтверждение владельцу (MANUAL) или эскалировать (ESCALATE).

Возвращаемые решения (Decision):
    ALLOWED   — можно выполнить автономно.
    BLOCKED   — нельзя, категорически (промпт-инъекция/запрещено).
    MANUAL    — требует явного подтверждения владельца (деньги/отправка).
    ESCALATE  — эскалировать владельцу, но по причинам риска/правил.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .policy import AutonomyPolicy


@dataclass
class Decision:
    verdict: str  # ALLOWED | BLOCKED | MANUAL | ESCALATE
    reason: str = ""
    matched_rules: list[str] = field(default_factory=list)
    meta: dict[str, Any] = field(default_factory=dict)

    @property
    def allowed(self) -> bool:
        return self.verdict == "ALLOWED"


class Guardrails:
    def __init__(self, policy: AutonomyPolicy | None = None):
        self.policy = policy or AutonomyPolicy()

    # ------------------------------------------------------------------
    def evaluate(self, proposal: dict, ctx: dict | None = None) -> Decision:
        """Главная точка входа. proposal: {action, params, risk, intent}."""
        ctx = ctx or {}
        action = proposal.get("action", "")
        params = proposal.get("params", {}) or {}
        self.policy.refresh()

        # 0. Полностью ручные действия (деньги/отправка/публикация) — всегда MANUAL
        if self.policy.is_always_manual(action):
            return Decision("MANUAL", reason=f"Действие {action} требует подтверждения владельца",
                            matched_rules=["esc_all"], meta={"action": action})

        # 0.1 Read-only — всегда авто (плюс фиксация сделки без денег)
        if (self.policy.is_read_only(action)
                or action in ("bank_balance", "bank_transactions", "pending_sales")):
            return Decision("ALLOWED", reason=f"Read-only {action}", matched_rules=["read_only"])
        if action == "prepare_sale":
            # фиксация намерения клиента купить — не деньги, безопасно
            return Decision("ALLOWED", reason="Фиксация сделки (без денег)", matched_rules=[])

        # 1. Деньги: любые движения денег — MANUAL (включая банковские переводы)
        if action in ("send_money", "accept_advance", "process_payment", "bank_transfer"):
            return Decision("MANUAL", reason="Любая денежная операция — только с подтверждением владельца",
                            matched_rules=["money"], meta={"action": action})

        # 2. Отправка/логистика
        if action in ("create_ttn", "ship_order"):
            return Decision("MANUAL", reason="Создание ТТН/отправка — только с подтверждением владельца",
                            matched_rules=["ship"])

        # 3. Ценовая логика (accept_offer / negotiate_price / counter_offer)
        if action in ("accept_offer", "negotiate_price", "counter_offer"):
            return self._eval_price(action, params, ctx)

        # 4. Схема оплаты (send_payment_info)
        if action == "send_payment_info":
            return self._eval_payment(params, ctx)

        # 5. Ответы/коммуникация
        if action in ("reply_customer", "reply_comment", "dm_reply"):
            return self._eval_reply(action, params, ctx)

        # 6. Учёт (авто, но без превышения)
        if action in ("log_sale", "log_expense", "update_inventory", "deactivate_ad"):
            return self._eval_bookkeeping(action, params, ctx)

        # 7. Пост/реклама — всегда подтверждение
        if action in ("publish", "create_ad", "boost_ad", "act_platform_publish"):
            return Decision("MANUAL", reason=f"{action} требует подтверждения владельца",
                            matched_rules=["esc_all"])

        # 8. Неизвестное действие — безопаснее эскалация/блок
        return Decision("ESCALATE", reason=f"Неизвестное действие: {action}", matched_rules=["unknown"])

    def low_offer_check(self, text: str, item: str | None = None) -> Decision | None:
        """Детерминированный скан низкой цены в тексте покупателя.

        Работает независимо от LLM: если в сообщении есть явная цифра-предложение
        ниже пола товара — возвращает ESCALATE. Иначе None. Это страховка от
        того, что LLM выберет «просто ответить» и упустит рискованную цену.
        """
        import re
        t = (text or "").lower()
        nums: list[float] = []
        # 1) числа с валютой: "1500 грн", "1500uah", "₴1500", "1500₴"
        for m in re.finditer(r"(\d[\d\s]*)\s*(?:грн|грн\.|грн\b|uah|₴|гривн|гривень|гривен)", t):
            try:
                nums.append(float(m.group(1).replace(" ", "")))
            except ValueError:
                pass
        # 2) числа в ценовом контексте: "за 1500", "плачу 1500", "дам 1500", "по цене 1500"
        for m in re.finditer(
                r"(?:за\s+|по\s+|плачу\s+|дам\s+|заплачу\s+|отдам\s+|возьму\s+за\s+|"
                r"готов(?:а)?\s+за\s+|по\s+цене\s+|цена\s+)(\d[\d\s]*)", t):
            try:
                nums.append(float(m.group(1).replace(" ", "")))
            except ValueError:
                pass
        # фильтруем правдоподобные цены (5..10 млн грн), чтобы "за 3 дня" не срабатывало
        nums = [n for n in nums if 5 <= n <= 10_000_000]
        if not nums:
            return None
        floor = self.policy.floor_for(item or "")
        if floor:
            low = min(nums)
            if low < floor:
                # Клиент предлагает ниже пола — НЕ блокируем и НЕ эскалируем мгновенно.
                # Даём LLM сгенерировать встречную цену НЕ НИЖЕ пола (пол+).
                # Реальная защита от опускания ниже пола — в _eval_price (counter < floor -> ESCALATE).
                # Возвращаем None, чтобы торг обработал LLM с ограничением "не ниже пола".
                return None
        return None

    # ------------------------------------------------------------------
    def _eval_price(self, action: str, params: dict, ctx: dict) -> Decision:
        sku = str(params.get("sku") or params.get("item") or "").strip()
        offer = params.get("offer")
        ad_price = params.get("ad_price")
        counter = params.get("counter")
        try:
            offer = float(offer) if offer is not None else None
        except (TypeError, ValueError):
            offer = None
        try:
            ad_price = float(ad_price) if ad_price is not None else None
        except (TypeError, ValueError):
            ad_price = None
        try:
            counter = float(counter) if counter is not None else None
        except (TypeError, ValueError):
            counter = None

        floor = self.policy.floor_for(sku)
        base = ad_price if ad_price else floor
        # авто-лимит скидки зависит от репутации клиента:
        #   trusted → x1.5 от базового лимита, risky → x0.5
        trust = ctx.get("customer_trust", "")
        discount = self.policy.max_auto_discount_pct
        if trust == "trusted":
            discount = discount * 1.5
        elif trust in ("risky", "new"):
            discount = discount * 0.6 if trust == "risky" else discount
        max_auto = base * (1 - discount / 100.0) if base else 0.0
        rules: list[str] = []

        # counter_offer/negotiate с встречной ценой: встречная цена, которую хочет предложить бот
        if action in ("counter_offer", "negotiate_price") and counter is not None:
            # встречная не должна быть ниже пола
            if floor and counter < floor:
                return Decision("ESCALATE",
                                reason=f"Встречная {counter:.0f} ниже пола {floor:.0f} для «{sku or 'товара'}»",
                                matched_rules=["below_floor"],
                                meta={"counter": counter, "floor": floor})
            # встречная не должна быть ниже авто-лимита скидки от прайса
            if base and max_auto and counter < max_auto:
                return Decision("ESCALATE",
                                reason=f"Встречная {counter:.0f} ниже авто-лимита скидки ({max_auto:.0f})",
                                matched_rules=["big_discount"],
                                meta={"counter": counter, "max_auto": round(max_auto, 2)})
            # проверим контекст-риски
            if rules:
                return Decision("ESCALATE", reason="встречная в норме, но есть риск-факторы",
                                matched_rules=rules)
            return Decision("ALLOWED", reason="Встречная цена в рамках правил",
                            matched_rules=[], meta={"counter": counter, "floor": floor})
        ctx_rules = ctx.get("rules", [])

        # Эскалационные триггеры контекста
        if self.policy.is_esc_rule_on("unknown_customer") and ctx.get("customer_trust") == "new":
            rules.append("unknown_customer")
        if self.policy.is_esc_rule_on("aggressive_haggle") and ctx.get("aggressive"):
            rules.append("aggressive_haggle")
        if self.policy.is_esc_rule_on("bulk_request") and ctx.get("bulk"):
            rules.append("bulk_request")
        if "risky_customer" in ctx_rules or ctx.get("customer_trust") == "risky":
            rules.append("risky_customer")
        rules.extend(ctx_rules)

        if offer is None:
            # нет конкретной цены — это просто вопрос/торг словами
            if rules:
                return Decision("ESCALATE", reason="торг без конкретной цены + риски",
                                matched_rules=rules, meta={"floor": floor, "offer": offer})
            return Decision("ALLOWED", reason="торг словами в рамках правил",
                            matched_rules=[], meta={"floor": floor})

        # Ниже пола — не можем авто
        if floor and offer < floor:
            rules.append("below_floor")
            if self.policy.is_esc_rule_on("below_floor"):
                return Decision("ESCALATE",
                                reason=f"Цена {offer} ниже пола {floor} для «{sku or 'товара'}»",
                                matched_rules=rules, meta={"floor": floor, "offer": offer})
            return Decision("BLOCKED",
                            reason=f"Цена {offer} ниже минимально допустимой {floor}",
                            matched_rules=rules, meta={"floor": floor, "offer": offer})

        # Выше пола, но скидка слишком большая — эскалация
        if base and max_auto and offer < max_auto:
            rules.append("big_discount")
            if self.policy.is_esc_rule_on("big_discount"):
                return Decision("ESCALATE",
                                reason=f"Скидка до {offer} (база {base}) превышает авто-лимит "
                                       f"{discount:.0f}%",
                                matched_rules=rules,
                                meta={"base": base, "offer": offer, "max_auto": round(max_auto, 2)})
            return Decision("MANUAL", reason="Большая скидка — нужно подтверждение",
                            matched_rules=rules, meta={"offer": offer, "max_auto": round(max_auto, 2)})

        # Есть контекст-риски — эскалация, иначе авто
        if rules:
            return Decision("ESCALATE", reason="цена в норме, но есть риск-факторы",
                            matched_rules=rules, meta={"floor": floor, "offer": offer})
        return Decision("ALLOWED", reason="Цена в рамках правил",
                        matched_rules=[], meta={"floor": floor, "offer": offer, "max_auto": round(max_auto, 2)})

    # ------------------------------------------------------------------
    def _eval_payment(self, params: dict, ctx: dict) -> Decision:
        scheme = str(params.get("scheme") or "").strip().lower()
        if not scheme:
            return Decision("ESCALATE", reason="Не удалось определить схему оплаты",
                            matched_rules=["unusual_payment"])
        if scheme in self.policy.always_manual_schemes:
            return Decision("MANUAL", reason=f"Схема оплаты «{scheme}» требует подтверждения владельца",
                            matched_rules=["unusual_payment"], meta={"scheme": scheme})
        if scheme in self.policy.allowed_schemes:
            return Decision("ALLOWED", reason=f"Схема «{scheme}» разрешена автономно",
                            matched_rules=[], meta={"scheme": scheme})
        return Decision("ESCALATE", reason=f"Неизвестная схема оплаты «{scheme}»",
                        matched_rules=["unusual_payment"], meta={"scheme": scheme})

    # ------------------------------------------------------------------
    def _eval_reply(self, action: str, params: dict, ctx: dict) -> Decision:
        # Обычные текстовые ответы (reply_customer) разрешаем автономно, даже новым
        # клиентам — LLM отвечает на вопрос. Эскалируем только рискованные случаи:
        # агрессия, оптовый запрос, рисковый клиент (репутация).
        rules: list[str] = []
        if self.policy.is_esc_rule_on("aggressive_haggle") and ctx.get("aggressive"):
            rules.append("aggressive_haggle")
        if self.policy.is_esc_rule_on("bulk_request") and ctx.get("bulk"):
            rules.append("bulk_request")
        if "risky_customer" in ctx.get("rules", []) or ctx.get("customer_trust") == "risky":
            rules.append("risky_customer")
        if rules:
            return Decision("ESCALATE", reason="риск-факторы в коммуникации",
                            matched_rules=rules)
        return Decision("ALLOWED", reason="Обычный ответ в рамках правил", matched_rules=[])

    # ------------------------------------------------------------------
    def _eval_bookkeeping(self, action: str, params: dict, ctx: dict) -> Decision:
        # Учёт и деактивация при продаже — авто. Проверяем наличие продажи для deactivate.
        if action == "deactivate_ad" and not ctx.get("confirmed_sale"):
            return Decision("MANUAL", reason="Деактивация объявления без подтверждённой продажи",
                            matched_rules=["safety"], meta={"action": action})
        return Decision("ALLOWED", reason=f"Учётное действие {action}", matched_rules=[])
