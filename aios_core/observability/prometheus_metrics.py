from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from starlette.responses import Response

MESSAGES_RECEIVED = Counter("aios_messages_total", "Total messages", ["platform"])
DRAFTS_CREATED = Counter("aios_drafts_created_total", "Total drafts")
PROCESSING_TIME = Histogram("aios_processing_seconds", "Processing time")

async def metrics_endpoint(request):
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)