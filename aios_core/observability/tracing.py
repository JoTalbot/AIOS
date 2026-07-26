import os
def init_tracing(service_name="aios"):
    endpoint = os.getenv("OTEL_EXPORTER_ENDPOINT")
    if not endpoint:
        print("[Tracing] OTEL not set")
        return None
    try:
        from opentelemetry import trace
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        from opentelemetry.sdk.resources import Resource
        resource = Resource.create({"service.name": service_name})
        provider = TracerProvider(resource=resource)
        exporter = OTLPSpanExporter(endpoint=endpoint)
        provider.add_span_processor(BatchSpanProcessor(exporter))
        trace.set_tracer_provider(provider)
        print(f"[Tracing] Initialized to {endpoint}")
        return provider
    except Exception as e:
        print(f"[Tracing] Error: {e}")
        return None
