import os

from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from starlette.responses import Response

MESSAGES_RECEIVED = Counter("aios_messages_total", "Total messages", ["platform"])
DRAFTS_CREATED = Counter("aios_drafts_created_total", "Total drafts")
PROCESSING_TIME = Histogram("aios_processing_seconds", "Processing time")


def _read_exporter_metrics() -> str:
    """Append auto-coder/exporter metrics (aios_service.prom) if available.

    The exporter writes to the shared data volume which the API container
    sees at /app/data/metrics_exporter/aios_service.prom.
    """
    paths = [
        "/app/data/metrics_exporter/aios_service.prom",
        "/root/AIOS/data/metrics_exporter/aios_service.prom",
    ]
    for p in paths:
        try:
            if os.path.exists(p):
                return open(p, encoding="utf-8", errors="ignore").read()
        except Exception:
            continue
    return ""


async def metrics_endpoint(request):
    body = generate_latest()
    extra = _read_exporter_metrics()
    if extra:
        body = body + b"\n" + extra.encode("utf-8")
    return Response(content=body, media_type=CONTENT_TYPE_LATEST)
