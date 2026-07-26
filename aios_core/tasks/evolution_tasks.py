
from aios_core.evolution.orchestrator import evolution_orchestrator
from aios_core.evolution.template_evolution import template_evolution
from aios_core.evolution.intent_discovery import intent_discovery
from aios_core.evolution.self_healing import self_healing
from aios_core.notifications.dispatcher import NotificationDispatcher
import os

dispatcher = NotificationDispatcher()

async def run_evolution_cycle(ctx):
    """Периодический запуск полного цикла эволюции."""
    result = await evolution_orchestrator.run_cycle()
    
    # Уведомление в Telegram если есть изменения
    if result.get("evolved"):
        emails = os.getenv("EVOLUTION_ALERT_EMAILS", "").split(",")
        if emails and emails[0]:
            await dispatcher.dispatch_escalation(
                "evolution",
                f"Evolution cycle completed: {len(result['evolved'])} templates evolved",
                emails=emails
            )
    
    return result

async def discover_new_intents(ctx, messages):
    """Анализ неопределенных сообщений для обнаружения новых интентов."""
    result = intent_discovery.analyze(messages)
    return result

async def heal_rejected_template(ctx, template, reason, original):
    """Self-healing отклоненного шаблона."""
    result = await self_healing.heal(template, reason, original)
    return result
