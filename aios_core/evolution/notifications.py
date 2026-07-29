
import os

from aios_core.notifications.dispatcher import NotificationDispatcher

dispatcher = NotificationDispatcher()

async def notify_template_promoted(template_id: str, old_version: int, new_version: int):
    """Уведомление о продвижении нового шаблона."""
    emails = os.getenv("EVOLUTION_ALERT_EMAILS", "").split(",")
    if emails and emails[0]:
        await dispatcher.dispatch_escalation(
            "evolution",
            f"Template {template_id} promoted: v{old_version} -> v{new_version}",
            emails=emails
        )

async def notify_new_intent(intent_name: str, message_count: int):
    """Уведомление о обнаружении нового интента."""
    emails = os.getenv("EVOLUTION_ALERT_EMAILS", "").split(",")
    if emails and emails[0]:
        await dispatcher.dispatch_escalation(
            "evolution",
            f"New intent discovered: {intent_name} ({message_count} messages)",
            emails=emails
        )

async def notify_self_heal(template_id: str, reason: str):
    """Уведомление о self-healing шаблона."""
    emails = os.getenv("EVOLUTION_ALERT_EMAILS", "").split(",")
    if emails and emails[0]:
        await dispatcher.dispatch_escalation(
            "evolution",
            f"Template {template_id} self-healed. Reason: {reason}",
            emails=emails
        )
