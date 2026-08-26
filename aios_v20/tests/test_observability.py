from aios_v20.observability.metrics import MetricsCollector


def test_metrics_collector():
    collector = MetricsCollector()
    event = collector.record("workflow.started")
    assert event.name == "workflow.started"
