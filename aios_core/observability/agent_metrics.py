import time
from functools import wraps

from prometheus_client import Counter, Gauge, Histogram

AGENT_REQUESTS = Counter(
    "aios_agent_requests_total",
    "Total requests to agents",
    ["agent_name", "action"]
)

AGENT_PROCESSING_TIME = Histogram(
    "aios_agent_processing_seconds",
    "Time spent processing by agents",
    ["agent_name"]
)

AGENT_CONFIDENCE = Histogram(
    "aios_agent_confidence",
    "Agent confidence distribution",
    ["agent_name"],
    buckets=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
)

ACTIVE_AGENTS = Gauge(
    "aios_active_agents",
    "Number of active agents"
)

def track_agent_metrics(agent_name: str):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start = time.time()
            try:
                result = await func(*args, **kwargs)
                action = result.result.get("action", "unknown") if result.result else "unknown"
                confidence = result.result.get("confidence", 0.0) if result.result else 0.0
                AGENT_REQUESTS.labels(agent_name=agent_name, action=action).inc()
                AGENT_CONFIDENCE.labels(agent_name=agent_name).observe(confidence)
                return result
            finally:
                duration = time.time() - start
                AGENT_PROCESSING_TIME.labels(agent_name=agent_name).observe(duration)
        return wrapper
    return decorator
