"""AIOS AI Advisor (H3.11) - Generative responses for platform Direct messages.

Gathers context from:
- Platform storage (OLX, Instagram, etc)
- Inbox history
- Memory manager
- Knowledge graph
- Constitution constraints

Provides:
- Draft-only replies (never auto-send, human-approve mandatory per Roadmap guardians)
- Inbox summarization
- Price advice from history
- Compliance guard integration
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .constitution_engine import ConstitutionEngine
from .knowledge_graph import KnowledgeGraph
from .memory_manager import MemoryManager


@dataclass
class AdvisorDraft:
    """Structured AI-generated reply draft with metadata."""
    id: str
    platform: str
    recipient: str
    original_message: str
    draft_reply: str
    confidence: float
    reasoning: str
    requires_approval: bool = True
    suggested_price: float | None = None
    context_used: list[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    template: str = "default"
    compliance_status: str = "pending"


@dataclass
class InboxSummary:
    """Aggregated inbox summary with urgency and sentiment."""
    platform: str
    total_messages: int
    unread: int
    urgent: List[dict[str, Any]]
    by_sender: dict[str, int]
    sentiment_overview: str
    action_items: list[str]
    generated_at: float = field(default_factory=time.time)


@dataclass
class PriceAdvice:
    """Pricing recommendation with confidence score."""
    platform: str
    item_id: str
    current_price: float
    suggested_price: float
    reason: str
    confidence: float
    market_data: dict[str, Any] = field(default_factory=dict)
    history_used: List[dict[str, Any]] = field(default_factory=list)


class TemplateRegistry:
    """Registry of response templates per platform."""

    def __init__(self):
        self.templates: Dict[str, dict[str, str]] = {
            "olx": {
                "greeting": "Добрый день! Спасибо за интерес к {item_title}.",
                "price_negotiation": "Понимаю ваше предложение {buyer_price} грн. Могу предложить {seller_price} грн, учитывая {reason}.",
                "availability": "Да, товар {item_title} в наличии. {details}",
                "meetup": "Могу встретиться {time}, район {location}. Удобно?",
                "default": "Спасибо за сообщение! {context} Уточните, пожалуйста, что именно интересует?",
                "closing": "Если есть вопросы — пишите, отвечу быстро!",
            },
            "instagram": {
                "greeting": "Привет! ✨ Спасибо за сообщение по {item_title}",
                "price": "Цена {price} грн, торг возможен 😉 {reason}",
                "default": "Привет! {context} Напиши подробнее — подскажу!",
                "closing": "Жду ответа 🙌",
            },
            "facebook": {
                "greeting": "Hi! Thanks for your interest in {item_title}.",
                "default": "Thanks for reaching out! {context} Let me know if you need more details.",
                "price": "Price is {price} UAH. {reason}",
            },
            "generic": {
                "default": 'Спасибо за сообщение: "{original}". {context}',
                "greeting": "Здравствуйте! Спасибо за обращение.",
                "closing": "С уважением!",
            },
        }

    def get(self, platform: str, template_name: str = "default") -> str:
        """Execute get."""
        plat = self.templates.get(platform.lower(), self.templates["generic"])
        return plat.get(template_name, plat.get("default", "Спасибо за сообщение!"))

    def render(self, platform: str, template_name: str, **kwargs) -> str:
        """Execute render."""
        tmpl = self.get(platform, template_name)
        try:
            return tmpl.format(**kwargs)
        except KeyError:
            # fallback without missing keys
            return tmpl


class AISalesAdvisor:
    """Main AI Advisor - draft-only, human-approve mandatory."""

    def __init__(
        self,
        memory: Optional[MemoryManager] = None,
        knowledge: Optional[KnowledgeGraph] = None,
        constitution: Optional[ConstitutionEngine] = None,
    ):
        self.memory = memory
        self.knowledge = knowledge
        self.constitution = constitution
        self.templates = TemplateRegistry()
        self._drafts: Dict[str, AdvisorDraft] = {}
        self.version = "1.0.0"

    def draft_reply(
        self,
        platform: str,
        original_message: str,
        recipient: str,
        item_context: dict[str, Any] | None = None,
        inbox_context: Optional[List[dict[str, Any]]] = None,
    ) -> AdvisorDraft:
        """Generate draft reply - NEVER auto-sends."""
        item_context = item_context or {}
        inbox_context = inbox_context or []

        # Build context from memory/knowledge if available
        context_used = []
        memory_snippets = []
        if self.memory:
            try:
                # search memory for recipient
                results = self.memory.search(query=recipient, limit=3)
                if results:
                    memory_snippets = [r.get("content", {}) for r in results[:2]]
                    context_used.append(f"memory:{len(memory_snippets)} snippets")
            except Exception:
                pass  # Memory search is advisory — skip on error

        # Determine intent
        intent = self._classify_intent(original_message)
        template_name = intent

        # Price logic
        suggested_price = None
        price_reason = ""
        if intent in ("price_negotiation", "price"):
            advice = self.price_advice(
                platform,
                item_context.get("id", "unknown"),
                item_context.get("price", 0),
            )
            suggested_price = advice.suggested_price if advice else None
            price_reason = advice.reason if advice else "состояние и рыночная цена"

        # Render draft
        context_text = self._build_context_text(item_context, memory_snippets, inbox_context)

        rendered = self.templates.render(
            platform,
            template_name,
            item_title=item_context.get("title", "товару"),
            buyer_price=self._extract_price(original_message) or "вашу цену",
            seller_price=(
                f"{suggested_price:.0f}" if suggested_price else f"{item_context.get('price', '')}"
            ),
            reason=price_reason,
            details=item_context.get("description", "")[:200],
            price=item_context.get("price", ""),
            original=original_message[:100],
            context=context_text,
            time="вечером",
            location="центр",
        )

        # Add closing
        closing = self.templates.render(platform, "closing", **item_context)
        full_reply = f"{rendered}\n\n{closing}".strip()

        # Constitutional check if engine provided
        compliance = "approved_draft"
        if self.constitution:
            try:
                result = self.constitution.evaluate(
                    {
                        "goal": "Generate draft reply",
                        "scope": f"platform:{platform} recipient:{recipient}",
                        "risk": "low",
                        "audit_log": True,
                        "agent_id": "ai_advisor",
                        "authority": "advisor",
                    }
                )
                if result.get("decision") == "DENY":
                    compliance = "denied"
                    full_reply = "[DRAFT BLOCKED BY CONSTITUTION] " + full_reply
            except Exception:
                compliance = "check_failed"

        draft_id = f"draft_{int(time.time()*1000)}_{hash(recipient) % 10000}"
        draft = AdvisorDraft(
            id=draft_id,
            platform=platform,
            recipient=recipient,
            original_message=original_message,
            draft_reply=full_reply,
            confidence=self._estimate_confidence(original_message, item_context, memory_snippets),
            reasoning=f"Intent={intent}, template={template_name}, context_items={len(context_used)+len(inbox_context)}",
            requires_approval=True,
            suggested_price=suggested_price,
            context_used=context_used,
            template=template_name,
            compliance_status=compliance,
        )
        self._drafts[draft_id] = draft
        return draft

    def summarize_inbox(self, platform: str, messages: List[dict[str, Any]]) -> InboxSummary:
        """Summarize inbox - for operator dashboard."""
        total = len(messages)
        unread = sum(1 for m in messages if not m.get("read", True))
        by_sender: dict[str, int] = {}
        urgent = []

        for m in messages:
            sender = m.get("sender", "unknown")
            by_sender[sender] = by_sender.get(sender, 0) + 1
            if any(
                k in m.get("text", "").lower()
                for k in ["срочно", "urgent", "сегодня", "куплю", "оплачу"]
            ):
                urgent.append(m)

        sentiment = "neutral"
        if total > 0:
            positive_keywords = ["спасибо", "куплю", "беру", "отлично"]
            pos_count = sum(
                1
                for m in messages
                if any(k in m.get("text", "").lower() for k in positive_keywords)
            )
            if pos_count / total > 0.5:
                sentiment = "positive"
            elif len(urgent) > total * 0.3:
                sentiment = "urgent"

        actions = []
        if unread > 0:
            actions.append(f"Ответить на {unread} непрочитанных")
        if urgent:
            actions.append(f"Приоритет: {len(urgent)} срочных")
        if total > 50:
            actions.append("Рассмотреть архивацию старых диалогов")

        return InboxSummary(
            platform=platform,
            total_messages=total,
            unread=unread,
            urgent=urgent[:5],
            by_sender=by_sender,
            sentiment_overview=sentiment,
            action_items=actions,
        )

    def price_advice(
        self,
        platform: str,
        item_id: str,
        current_price: float,
        market_samples: Optional[list[float]] = None,
    ) -> Optional[PriceAdvice]:
        """Generate price advice from history and market."""
        market_samples = market_samples or []
        if self.memory:
            try:
                # Look for similar items
                mem = self.memory.search(query=str(item_id), limit=5)
                for entry in mem:
                    if isinstance(entry, dict) and "price" in str(entry).lower():
                        # naive extraction
                        pass  # TODO: structured price extraction from memory
            except Exception:
                pass  # Market sample extraction failed — proceed without samples

        if not market_samples:
            suggested = current_price * 0.95 if current_price > 100 else current_price
            reason = "Рекомендация -5% для ускорения продажи (нет рыночных данных)"
            confidence = 0.4
        else:
            avg_market = sum(market_samples) / len(market_samples)
            if current_price > avg_market * 1.1:
                suggested = avg_market * 1.05
                reason = f"Ваша цена выше рынка ({avg_market:.0f} средн.), рекомендуем снизить к {suggested:.0f}"
            elif current_price < avg_market * 0.85:
                suggested = avg_market * 0.95
                reason = (
                    f"Цена ниже рынка, можно повысить до {suggested:.0f} и сохранить конкурентность"
                )
            else:
                suggested = current_price * 0.98
                reason = f"Цена немного выше среднего ({avg_market:.0f}), легкая коррекция к {suggested:.0f} ускорит продажу"
            confidence = 0.75

        return PriceAdvice(
            platform=platform,
            item_id=item_id,
            current_price=current_price,
            suggested_price=float(suggested),
            reason=reason,
            confidence=confidence,
            market_data={
                "avg_market": (sum(market_samples) / len(market_samples) if market_samples else 0),
                "samples": len(market_samples),
            },
            history_used=[],
        )

    # --- internal helpers ---

    def _classify_intent(self, text: str) -> str:
        t = text.lower()
        if any(k in t for k in ["сколько", "цена", "uah", "грн", "$", "торг"]):
            return (
                "price_negotiation" if any(k in t for k in ["торг", "скидк", "дешевл"]) else "price"
            )
        if any(k in t for k in ["есть", "наличии", "доступен"]):
            return "availability"
        if any(k in t for k in ["встрет", "забрать", "где", "когда", "достав"]):
            return "meetup"
        if any(k in t for k in ["привет", "здрав", "добрый"]):
            return "greeting"
        return "default"

    def _extract_price(self, text: str) -> str | None:
        import re

        m = re.search(r"(\d{2,6})\s*(грн|uah|\$)", text.lower())
        if m:
            return m.group(0)
        m = re.search(r"\b\d{3,6}\b", text)
        if m:
            return m.group(0)
        return None

    def _build_context_text(
        self,
        item_ctx: dict[str, Any],
        memory_snippets: list[Any],
        inbox_ctx: List[dict[str, Any]],
    ) -> str:
        parts = []
        if item_ctx.get("title"):
            parts.append(f"по объявлению '{item_ctx['title']}'")
        if memory_snippets:
            parts.append(f"учтена история ({len(memory_snippets)} заметок)")
        if inbox_ctx:
            parts.append(f"последних {len(inbox_ctx)} сообщений в диалоге")
        return " ".join(parts) if parts else "готов уточнить детали"

    def _estimate_confidence(
        self, original: str, item_ctx: dict[str, Any], memory_snippets: list[Any]
    ) -> float:
        score = 0.5
        if item_ctx.get("title"):
            score += 0.1
        if item_ctx.get("price"):
            score += 0.1
        if memory_snippets:
            score += 0.15
        if len(original) > 20:
            score += 0.05
        return min(score, 0.95)

    def list_drafts(self) -> List[AdvisorDraft]:
        """Execute list drafts."""
        return list(self._drafts.values())

    def get_draft(self, draft_id: str) -> Optional[AdvisorDraft]:
        """Execute get draft."""
        return self._drafts.get(draft_id)

    def approve_draft(self, draft_id: str, approved_by: str) -> Optional[AdvisorDraft]:
        """Mark draft as approved - actual sending must be done via outbox/CLI."""
        d = self._drafts.get(draft_id)
        if d:
            d.compliance_status = f"approved_by_{approved_by}"
            d.requires_approval = False
        return d
