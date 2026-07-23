"""Comprehensive tests for AIOS Telemetry module."""

import pytest

from aios_core.telemetry import MetricCounter, MetricGauge, MetricHistogram, Telemetry


class TestMetricCounter:
    """Tests for MetricCounter."""

    def test_counter_initialization(self):
        """Test counter initializes correctly."""
        counter = MetricCounter("test_counter", "Test description")
        assert counter.name == "test_counter"
        assert counter.description == "Test description"
        assert counter.value == 0.0

    def test_counter_add(self):
        """Test counter add operation."""
        counter = MetricCounter("requests")
        counter.add()
        assert counter.value == 1.0

        counter.add(5.0)
        assert counter.value == 6.0

    def test_counter_multiple_adds(self):
        """Test multiple counter additions."""
        counter = MetricCounter("events")
        for _ in range(10):
            counter.add()
        assert counter.value == 10.0


class TestMetricGauge:
    """Tests for MetricGauge."""

    def test_gauge_initialization(self):
        """Test gauge initializes correctly."""
        gauge = MetricGauge("temperature", "Current temperature")
        assert gauge.name == "temperature"
        assert gauge.description == "Current temperature"
        assert gauge.value == 0.0

    def test_gauge_set(self):
        """Test gauge set operation."""
        gauge = MetricGauge("connections")
        gauge.set(42.0)
        assert gauge.value == 42.0

        gauge.set(100.0)
        assert gauge.value == 100.0

    def test_gauge_can_decrease(self):
        """Test gauge can decrease value."""
        gauge = MetricGauge("active_users")
        gauge.set(100.0)
        gauge.set(50.0)
        assert gauge.value == 50.0


class TestMetricHistogram:
    """Tests for MetricHistogram."""

    def test_histogram_initialization(self):
        """Test histogram initializes correctly."""
        hist = MetricHistogram("request_duration", "Request duration in ms")
        assert hist.name == "request_duration"
        assert hist.description == "Request duration in ms"
        assert len(hist.values) == 0

    def test_histogram_observe(self):
        """Test histogram observe operation."""
        hist = MetricHistogram("latency")
        hist.observe(10.0)
        hist.observe(20.0)
        hist.observe(30.0)
        assert len(hist.values) == 3
        assert hist.values == [10.0, 20.0, 30.0]

    def test_histogram_summary_empty(self):
        """Test histogram summary when empty."""
        hist = MetricHistogram("test")
        summary = hist.get_summary()

        assert summary["count"] == 0
        assert summary["min"] == 0
        assert summary["max"] == 0
        assert summary["mean"] == 0
        assert summary["p50"] == 0
        assert summary["p95"] == 0
        assert summary["p99"] == 0

    def test_histogram_summary_with_values(self):
        """Test histogram summary with values."""
        hist = MetricHistogram("response_time")

        # Add 100 values from 1 to 100
        for i in range(1, 101):
            hist.observe(float(i))

        summary = hist.get_summary()

        assert summary["count"] == 100
        assert summary["min"] == 1.0
        assert summary["max"] == 100.0
        assert summary["mean"] == 50.5
        assert summary["p50"] >= 49.0  # Median
        assert summary["p95"] >= 94.0  # 95th percentile
        assert summary["p99"] >= 98.0  # 99th percentile

    def test_histogram_max_values_limit(self):
        """Test histogram limits to 5000 values."""
        hist = MetricHistogram("test")

        # Add 6000 values
        for i in range(6000):
            hist.observe(float(i))

        # Should keep only last 5000
        assert len(hist.values) == 5000
        assert hist.values[0] == 1000.0  # First 1000 were dropped


class TestTelemetry:
    """Tests for Telemetry class."""

    @pytest.fixture
    def telemetry(self):
        """Create telemetry instance."""
        return Telemetry()

    def test_telemetry_initialization(self, telemetry):
        """Test telemetry initializes correctly."""
        assert telemetry is not None
        assert len(telemetry.counters) == 0
        assert len(telemetry.gauges) == 0
        assert len(telemetry.histograms) == 0

    def test_create_counter(self, telemetry):
        """Test creating a counter."""
        counter = telemetry.create_counter("requests_total", "Total requests")

        assert counter is not None
        assert counter.name == "requests_total"
        assert "requests_total" in telemetry.counters

    def test_create_gauge(self, telemetry):
        """Test creating a gauge."""
        gauge = telemetry.create_gauge("active_connections", "Active connections")

        assert gauge is not None
        assert gauge.name == "active_connections"
        assert "active_connections" in telemetry.gauges

    def test_create_histogram(self, telemetry):
        """Test creating a histogram."""
        hist = telemetry.create_histogram("request_duration_ms", "Request duration")

        assert hist is not None
        assert hist.name == "request_duration_ms"
        assert "request_duration_ms" in telemetry.histograms

    def test_increment_counter(self, telemetry):
        """Test incrementing a counter."""
        telemetry.create_counter("events")
        telemetry.increment_counter("events")
        telemetry.increment_counter("events", 5.0)

        assert telemetry.counters["events"].value == 6.0

    def test_set_gauge(self, telemetry):
        """Test setting a gauge value."""
        telemetry.create_gauge("temperature")
        telemetry.set_gauge("temperature", 22.5)

        assert telemetry.gauges["temperature"].value == 22.5

    def test_observe_histogram(self, telemetry):
        """Test observing a histogram value."""
        telemetry.create_histogram("latency")
        telemetry.observe_histogram("latency", 10.0)
        telemetry.observe_histogram("latency", 20.0)

        assert len(telemetry.histograms["latency"].values) == 2

    def test_get_counter_value(self, telemetry):
        """Test getting counter value."""
        telemetry.create_counter("test")
        telemetry.increment_counter("test", 42.0)

        value = telemetry.get_counter_value("test")
        assert value == 42.0

    def test_get_gauge_value(self, telemetry):
        """Test getting gauge value."""
        telemetry.create_gauge("test")
        telemetry.set_gauge("test", 99.0)

        value = telemetry.get_gauge_value("test")
        assert value == 99.0

    def test_get_histogram_summary(self, telemetry):
        """Test getting histogram summary."""
        telemetry.create_histogram("test")

        for i in range(100):
            telemetry.observe_histogram("test", float(i))

        summary = telemetry.get_histogram_summary("test")

        assert summary["count"] == 100
        assert "mean" in summary
        assert "p50" in summary
        assert "p95" in summary

    def test_increment_nonexistent_counter(self, telemetry):
        """Test incrementing non-existent counter creates it."""
        telemetry.increment_counter("new_counter", 10.0)

        assert "new_counter" in telemetry.counters
        assert telemetry.counters["new_counter"].value == 10.0

    def test_set_nonexistent_gauge(self, telemetry):
        """Test setting non-existent gauge creates it."""
        telemetry.set_gauge("new_gauge", 50.0)

        assert "new_gauge" in telemetry.gauges
        assert telemetry.gauges["new_gauge"].value == 50.0

    def test_observe_nonexistent_histogram(self, telemetry):
        """Test observing non-existent histogram creates it."""
        telemetry.observe_histogram("new_histogram", 25.0)

        assert "new_histogram" in telemetry.histograms
        assert len(telemetry.histograms["new_histogram"].values) == 1

    def test_export_prometheus_format(self, telemetry):
        """Test exporting metrics in Prometheus format."""
        telemetry.create_counter("requests", "Total requests")
        telemetry.increment_counter("requests", 100.0)

        telemetry.create_gauge("connections", "Active connections")
        telemetry.set_gauge("connections", 42.0)

        telemetry.create_histogram("duration", "Request duration")
        telemetry.observe_histogram("duration", 10.0)
        telemetry.observe_histogram("duration", 20.0)

        output = telemetry.export_prometheus()

        # Check format
        assert "# HELP requests Total requests" in output
        assert "# TYPE requests counter" in output
        assert "requests 100.0" in output

        assert "# HELP connections Active connections" in output
        assert "# TYPE connections gauge" in output
        assert "connections 42.0" in output

        assert "# TYPE duration histogram" in output

    def test_export_json_format(self, telemetry):
        """Test exporting metrics in JSON format."""
        telemetry.create_counter("test_counter")
        telemetry.increment_counter("test_counter", 50.0)

        telemetry.create_gauge("test_gauge")
        telemetry.set_gauge("test_gauge", 75.0)

        output = telemetry.export_json()

        assert "counters" in output
        assert "gauges" in output
        assert output["counters"]["test_counter"] == 50.0
        assert output["gauges"]["test_gauge"] == 75.0

    def test_reset_metrics(self, telemetry):
        """Test resetting all metrics."""
        telemetry.create_counter("counter")
        telemetry.increment_counter("counter", 100.0)

        telemetry.create_gauge("gauge")
        telemetry.set_gauge("gauge", 50.0)

        telemetry.reset()

        assert len(telemetry.counters) == 0
        assert len(telemetry.gauges) == 0
        assert len(telemetry.histograms) == 0

    def test_get_all_metrics(self, telemetry):
        """Test getting all metrics."""
        telemetry.create_counter("c1")
        telemetry.create_counter("c2")
        telemetry.create_gauge("g1")
        telemetry.create_histogram("h1")

        metrics = telemetry.get_all_metrics()

        assert len(metrics["counters"]) == 2
        assert len(metrics["gauges"]) == 1
        assert len(metrics["histograms"]) == 1

    def test_multiple_counters_independent(self, telemetry):
        """Test multiple counters are independent."""
        telemetry.create_counter("counter1")
        telemetry.create_counter("counter2")

        telemetry.increment_counter("counter1", 10.0)
        telemetry.increment_counter("counter2", 20.0)

        assert telemetry.counters["counter1"].value == 10.0
        assert telemetry.counters["counter2"].value == 20.0

    def test_histogram_percentile_accuracy(self, telemetry):
        """Test histogram percentile calculations."""
        telemetry.create_histogram("latency")

        # Add values 1-1000
        for i in range(1, 1001):
            telemetry.observe_histogram("latency", float(i))

        summary = telemetry.get_histogram_summary("latency")

        # Check percentiles are reasonable
        assert 490 <= summary["p50"] <= 510  # Median ~500
        assert 940 <= summary["p95"] <= 960  # P95 ~950
        assert 980 <= summary["p99"] <= 1000  # P99 ~990


class TestTelemetryEdgeCases:
    """Edge case tests for Telemetry."""

    @pytest.fixture
    def telemetry(self):
        return Telemetry()

    def test_negative_counter_value(self, telemetry):
        """Test counter can handle negative increments."""
        telemetry.create_counter("test")
        telemetry.increment_counter("test", -5.0)

        assert telemetry.counters["test"].value == -5.0

    def test_zero_gauge_value(self, telemetry):
        """Test gauge can be set to zero."""
        telemetry.create_gauge("test")
        telemetry.set_gauge("test", 0.0)

        assert telemetry.gauges["test"].value == 0.0

    def test_very_large_histogram_values(self, telemetry):
        """Test histogram handles very large values."""
        telemetry.create_histogram("test")
        telemetry.observe_histogram("test", 1e10)
        telemetry.observe_histogram("test", 1e20)

        summary = telemetry.get_histogram_summary("test")
        assert summary["max"] == 1e20

    def test_empty_export(self, telemetry):
        """Test exporting when no metrics exist."""
        prometheus = telemetry.export_prometheus()
        json_data = telemetry.export_json()

        assert prometheus == ""
        assert json_data["counters"] == {}
        assert json_data["gauges"] == {}
        assert json_data["histograms"] == {}
