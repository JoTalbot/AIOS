
from prometheus_client import Counter, Histogram

EVOLUTION_CYCLES = Counter(
    "aios_evolution_cycles_total",
    "Total evolution cycles executed"
)

TEMPLATES_PROMOTED = Counter(
    "aios_templates_promoted_total",
    "Total templates promoted through A/B testing",
    ["template_id"]
)

NEW_INTENTS_DISCOVERED = Counter(
    "aios_new_intents_discovered_total",
    "Total new intents discovered",
    ["intent_name"]
)

SELF_HEAL_ATTEMPTS = Counter(
    "aios_self_heal_attempts_total",
    "Total self-healing attempts",
    ["status"]
)

EVOLUTION_CYCLE_DURATION = Histogram(
    "aios_evolution_cycle_duration_seconds",
    "Time spent in evolution cycle"
)

def record_cycle():
    EVOLUTION_CYCLES.inc()

def record_promotion(template_id: str):
    TEMPLATES_PROMOTED.labels(template_id=template_id).inc()

def record_new_intent(intent_name: str):
    NEW_INTENTS_DISCOVERED.labels(intent_name=intent_name).inc()

def record_self_heal(status: str):
    SELF_HEAL_ATTEMPTS.labels(status=status).inc()
