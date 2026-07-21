"""Tests for OpenTelemetry Metrics and W3C Tracing (Milestone 4.2.2)."""

import pytest
import logging
from aios_core.telemetry import Telemetry
from aios_core.tracing import Tracer
from aios_core.logging_config import JSONFormatter, setup_logging


def test_telemetry_metrics():
    tel = Telemetry()

    # Counter
    cnt = tel.counter("tasks_processed", "Total tasks processed")
    cnt.add(1.0)
    cnt.add(2.0)
    assert cnt.value == 3.0

    # Gauge
    g = tel.gauge("memory_usage_mb", "Current memory in MB")
    g.set(512.4)
    assert g.value == 512.4

    # Histogram
    hist = tel.histogram("execution_latency_ms", "Task latency distribution")
    for val in [10.0, 20.0, 30.0, 40.0, 100.0]:
        hist.observe(val)

    summary = hist.get_summary()
    assert summary["count"] == 5
    assert summary["min"] == 10.0
    assert summary["max"] == 100.0
    assert summary["p50"] == 30.0

    # Prometheus export
    prom_out = tel.export_prometheus_format()
    assert "tasks_processed" in prom_out
    assert "execution_latency_ms_count" in prom_out


def test_w3c_tracer():
    tracer = Tracer()

    # Parse header
    t_id, s_id = tracer.parse_w3c_header("00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01")
    assert t_id == "4bf92f3577b34da6a3ce929d0e0e4736"
    assert s_id == "00f067aa0ba902b7"

    # Contextual span
    with tracer.start_span("orchestrator_execute") as root_span:
        root_span.set_attribute("agent_id", "agent_alpha")
        root_span.add_event("subtask_started", {"subtask": "fetch_data"})

        header = root_span.to_w3c_header()
        assert header.startswith("00-")

        # Nested span
        with tracer.start_span("nested_capability_run") as child_span:
            assert child_span.trace_id == root_span.trace_id
            assert child_span.parent_id == root_span.span_id

    assert tracer.stats()["finished_spans"] >= 2


def test_json_logging_formatter():
    formatter = JSONFormatter()
    logger = logging.getLogger("aios_test")
    record = logger.makeRecord("aios_test", logging.INFO, "test.py", 10, "Test log message", (), None)

    formatted = formatter.format(record)
    assert '"message": "Test log message"' in formatted
    assert '"level": "INFO"' in formatted
    assert '"constitutional_status": "VALID"' in formatted
