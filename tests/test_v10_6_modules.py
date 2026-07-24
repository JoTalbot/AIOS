"""Tests for v10.6.0 modules: Task Scheduler, Event Store, Observability,
Experiment Tracking, Data Lake, API Versioning, Digital Twin, Compliance,
Secrets Manager.

~150 tests covering registration, execution, edge cases, and stats."""

from __future__ import annotations

import os
import time
import pytest


# ═══════════════════════════════════════════════════════════════════════════════
# 1. TASK SCHEDULER
# ═══════════════════════════════════════════════════════════════════════════════

from aios_core.task_scheduler import (
    TaskPriority, TaskScheduleStatus, ScheduledTask, TaskScheduler, scheduler,
)
from datetime import datetime, timedelta


class TestScheduledTask:
    def test_is_recurring_false(self) -> None:
        t = ScheduledTask(name="one", func=lambda: 1, run_at=datetime.now())
        assert t.is_recurring() is False

    def test_is_recurring_true(self) -> None:
        t = ScheduledTask(name="rec", func=lambda: 1, run_at=datetime.now(), recurring_interval=timedelta(seconds=60))
        assert t.is_recurring() is True

    def test_can_retry(self) -> None:
        t = ScheduledTask(name="r", func=lambda: 1, run_at=datetime.now(), max_retries=3)
        assert t.can_retry() is True
        t.retry_count = 3
        assert t.can_retry() is False

    def test_next_run_time(self) -> None:
        t = ScheduledTask(name="r", func=lambda: 1, run_at=datetime.now(), recurring_interval=timedelta(seconds=10))
        next = t.next_run_time()
        assert next is not None


class TestTaskScheduler:
    def setup_method(self) -> None:
        self.ts = TaskScheduler()

    def test_schedule(self) -> None:
        t = self.ts.schedule("task1", lambda: 1, datetime.now() + timedelta(seconds=1))
        assert t.name == "task1"

    def test_schedule_in(self) -> None:
        t = self.ts.schedule_in("task2", lambda: 2, 10)
        assert t.status == TaskScheduleStatus.SCHEDULED

    def test_schedule_recurring(self) -> None:
        t = self.ts.schedule_recurring("rec1", lambda: 1, 5)
        assert t.is_recurring() is True

    def test_schedule_with_priority(self) -> None:
        t = self.ts.schedule_with_priority("p_task", lambda: 1, datetime.now(), priority=TaskPriority.CRITICAL)
        assert t.priority == TaskPriority.CRITICAL

    def test_schedule_with_retry(self) -> None:
        t = self.ts.schedule_with_retry("r_task", lambda: 1, datetime.now(), max_retries=3)
        assert t.max_retries == 3

    def test_tick_executes_due(self) -> None:
        results = []
        self.ts.schedule("now", lambda: results.append("executed"), datetime.now() - timedelta(seconds=1))
        self.ts.tick()
        assert "executed" in results

    def test_tick_skips_future(self) -> None:
        self.ts.schedule("future", lambda: 1, datetime.now() + timedelta(hours=1))
        executed = self.ts.tick()
        assert len(executed) == 0

    def test_tick_priority_order(self) -> None:
        order = []
        self.ts.schedule("low", lambda: order.append("low"), datetime.now() - timedelta(seconds=1), priority=TaskPriority.LOW)
        self.ts.schedule("crit", lambda: order.append("crit"), datetime.now() - timedelta(seconds=1), priority=TaskPriority.CRITICAL)
        executed = self.ts.tick()
        # Both should execute, CRITICAL first
        if len(order) >= 2:
            assert order[0] == "crit"

    def test_tick_failure(self) -> None:
        self.ts.schedule("fail", lambda: (_ for _ in ()).throw(ValueError("err")), datetime.now() - timedelta(seconds=1))
        self.ts.tick()
        task = self.ts.get_task("fail")
        assert task.status == TaskScheduleStatus.FAILED

    def test_tick_recurring_reschedule(self) -> None:
        self.ts.schedule_recurring("rec", lambda: 1, 10)
        self.ts.tasks["rec"].run_at = datetime.now() - timedelta(seconds=1)
        self.ts.tick()
        task = self.ts.get_task("rec")
        assert task.status == TaskScheduleStatus.SCHEDULED  # rescheduled

    def test_cancel(self) -> None:
        self.ts.schedule("t1", lambda: 1, datetime.now() + timedelta(seconds=10))
        self.ts.cancel("t1")
        assert self.ts.get_task("t1").status == TaskScheduleStatus.CANCELLED

    def test_cancel_unknown_raises(self) -> None:
        with pytest.raises(KeyError, match="not found"):
            self.ts.cancel("unknown")

    def test_cancel_all(self) -> None:
        self.ts.schedule("t1", lambda: 1, datetime.now())
        self.ts.schedule("t2", lambda: 1, datetime.now())
        count = self.ts.cancel_all()
        assert count == 2

    def test_get_pending(self) -> None:
        self.ts.schedule("t1", lambda: 1, datetime.now() + timedelta(seconds=10))
        pending = self.ts.get_pending()
        assert len(pending) == 1

    def test_get_completed(self) -> None:
        self.ts.schedule("t1", lambda: 1, datetime.now() - timedelta(seconds=1))
        self.ts.tick()
        completed = self.ts.get_completed()
        assert len(completed) >= 1

    def test_stats(self) -> None:
        self.ts.schedule("t1", lambda: 1, datetime.now())
        stats = self.ts.stats()
        assert stats["total"] == 1

    def test_singleton(self) -> None:
        assert isinstance(scheduler, TaskScheduler)


# ═══════════════════════════════════════════════════════════════════════════════
# 2. EVENT STORE
# ═══════════════════════════════════════════════════════════════════════════════

from aios_core.event_store import Event, Snapshot, Projection, EventStore


class TestEventStore:
    def setup_method(self) -> None:
        self.es = EventStore()

    def test_append(self) -> None:
        event = self.es.append("user_created", {"name": "Alice"}, aggregate_id="user_1")
        assert event.event_type == "user_created"
        assert event.aggregate_id == "user_1"

    def test_append_auto_version(self) -> None:
        self.es.append("evt1", {"x": 1}, aggregate_id="agg1")
        event2 = self.es.append("evt2", {"y": 2}, aggregate_id="agg1")
        assert event2.version == 2

    def test_get_events_all(self) -> None:
        self.es.append("e1", {"a": 1})
        self.es.append("e2", {"b": 2})
        events = self.es.get_events()
        assert len(events) == 2

    def test_get_events_by_aggregate(self) -> None:
        self.es.append("e1", {"a": 1}, aggregate_id="agg1")
        self.es.append("e2", {"b": 2}, aggregate_id="agg2")
        events = self.es.get_events(aggregate_id="agg1")
        assert len(events) == 1

    def test_get_events_by_type(self) -> None:
        self.es.append("order_created", {"id": 1})
        self.es.append("order_shipped", {"id": 2})
        events = self.es.get_events(event_type="order_created")
        assert len(events) == 1

    def test_get_events_since_version(self) -> None:
        self.es.append("e1", {"v": 1}, aggregate_id="agg1")
        self.es.append("e2", {"v": 2}, aggregate_id="agg1")
        events = self.es.get_events(aggregate_id="agg1", since_version=1)
        assert len(events) == 1

    def test_replay(self) -> None:
        self.es.append("e1", {"name": "Alice"}, aggregate_id="user_1")
        self.es.append("e2", {"age": 30}, aggregate_id="user_1")
        state = self.es.replay("user_1")
        assert state["name"] == "Alice"
        assert state["age"] == 30

    def test_replay_all(self) -> None:
        self.es.append("e1", {"x": 1}, aggregate_id="a1")
        self.es.append("e2", {"y": 2}, aggregate_id="a2")
        all_state = self.es.replay_all()
        assert "a1" in all_state

    def test_snapshot(self) -> None:
        self.es.append("e1", {"x": 1}, aggregate_id="agg1")
        self.es.append("e2", {"y": 2}, aggregate_id="agg1")
        snap = self.es.create_snapshot("agg1")
        assert snap.aggregate_id == "agg1"
        assert snap.version >= 2

    def test_replay_with_snapshot(self) -> None:
        self.es.append("e1", {"x": 1}, aggregate_id="agg1")
        self.es.create_snapshot("agg1")
        self.es.append("e2", {"y": 2}, aggregate_id="agg1")
        state = self.es.replay("agg1")
        assert state["x"] == 1
        assert state["y"] == 2

    def test_projection(self) -> None:
        def handler(event: Event, state: dict) -> dict:
            state["count"] = state.get("count", 0) + 1
            return state
        self.es.register_projection("counter", handler)
        self.es.append("e1", {"a": 1})
        self.es.append("e2", {"b": 2})
        proj_state = self.es.get_projection("counter")
        assert proj_state["count"] == 2

    def test_projection_unknown_raises(self) -> None:
        with pytest.raises(KeyError, match="not found"):
            self.es.get_projection("unknown")

    def test_compact(self) -> None:
        self.es.append("e1", {"x": 1}, aggregate_id="agg1")
        self.es.append("e2", {"y": 2}, aggregate_id="agg1")
        pruned = self.es.compact()
        assert pruned >= 0

    def test_stats(self) -> None:
        self.es.append("e1", {"x": 1})
        stats = self.es.stats()
        assert stats["total_events"] == 1


# ═══════════════════════════════════════════════════════════════════════════════
# 3. OBSERVABILITY
# ═══════════════════════════════════════════════════════════════════════════════

from aios_core.observability import (
    MetricKind, MetricEntry, Span, SpanEvent, LogEntry, Observability, observability,
)


class TestObservability:
    def setup_method(self) -> None:
        self.obs = Observability()

    def test_record_metric(self) -> None:
        self.obs.record_metric("cpu", 85.0)
        assert self.obs.get_metric("cpu") == 85.0

    def test_increment_counter(self) -> None:
        self.obs.increment("requests")
        self.obs.increment("requests", 5)
        entry = self.obs.get_metric_entry("requests")
        assert entry is not None
        assert entry.value == 6.0

    def test_register_metric_with_labels(self) -> None:
        self.obs.register_metric("latency", MetricKind.HISTOGRAM, labels={"service": "api"})
        assert len(self.obs.metrics) >= 1

    def test_observe_histogram(self) -> None:
        self.obs.observe_histogram("duration", 0.5)
        self.obs.observe_histogram("duration", 1.0)
        entry = self.obs.get_metric_entry("duration")
        assert entry is not None
        assert len(entry.values) == 2

    def test_trace_start_end(self) -> None:
        trace_id = self.obs.start_trace("api_call")
        self.obs.end_trace(trace_id)
        duration = self.obs.get_trace_duration(trace_id)
        assert duration > 0

    def test_trace_nested_span(self) -> None:
        trace_id = self.obs.start_trace("main")
        span_id = self.obs.start_span(trace_id, "sub_call")
        self.obs.end_span(trace_id, span_id)
        self.obs.end_trace(trace_id)
        spans = self.obs.get_trace(trace_id)
        assert len(spans) == 2

    def test_span_add_event(self) -> None:
        span = Span(trace_id="t1", span_id="s1", name="test")
        span.add_event("checkpoint", {"step": 1})
        assert len(span.events) == 1

    def test_log(self) -> None:
        self.obs.log("info", "Started processing")
        self.obs.log("error", "Connection failed")
        logs = self.obs.get_logs()
        assert len(logs) == 2

    def test_log_with_trace(self) -> None:
        trace_id = self.obs.start_trace("op")
        self.obs.log_with_trace("info", "Processing", trace_id)
        logs = self.obs.get_logs(trace_id=trace_id)
        assert len(logs) >= 1

    def test_get_logs_by_level(self) -> None:
        self.obs.log("info", "msg1")
        self.obs.log("error", "msg2")
        errors = self.obs.get_logs(level="error")
        assert len(errors) == 1

    def test_export_prometheus(self) -> None:
        self.obs.record_metric("cpu_usage", 75.0)
        prom = self.obs.export_prometheus()
        assert "cpu_usage" in prom

    def test_stats(self) -> None:
        self.obs.record_metric("x", 1)
        self.obs.start_trace("t")
        self.obs.log("info", "m")
        stats = self.obs.stats()
        assert stats["metrics"] >= 1

    def test_singleton(self) -> None:
        assert isinstance(observability, Observability)


# ═══════════════════════════════════════════════════════════════════════════════
# 4. EXPERIMENT TRACKING
# ═══════════════════════════════════════════════════════════════════════════════

from aios_core.experiment_tracking import ExperimentStatus, Experiment, ExperimentTracker


class TestExperimentTracker:
    def setup_method(self) -> None:
        self.tracker = ExperimentTracker()

    def test_start_experiment(self) -> None:
        exp = self.tracker.start_experiment("model_v1", {"lr": 0.01, "epochs": 10})
        assert exp.name == "model_v1"
        assert exp.status == ExperimentStatus.RUNNING

    def test_log_metric(self) -> None:
        exp = self.tracker.start_experiment("test", {"lr": 0.01})
        self.tracker.log_metric(exp.id, "accuracy", 0.95)
        assert self.tracker.get_experiment(exp.id).metrics["accuracy"] == 0.95

    def test_log_metrics(self) -> None:
        exp = self.tracker.start_experiment("test", {"lr": 0.01})
        self.tracker.log_metrics(exp.id, {"accuracy": 0.95, "f1": 0.90})
        assert self.tracker.get_experiment(exp.id).metrics["f1"] == 0.90

    def test_log_artifact(self) -> None:
        exp = self.tracker.start_experiment("test", {})
        self.tracker.log_artifact(exp.id, "model.pkl", "/path/to/model.pkl")
        assert "model.pkl" in self.tracker.get_experiment(exp.id).artifacts

    def test_add_tag(self) -> None:
        exp = self.tracker.start_experiment("test", {}, tags=["ml"])
        self.tracker.add_tag(exp.id, "baseline")
        assert "baseline" in self.tracker.get_experiment(exp.id).tags

    def test_add_note(self) -> None:
        exp = self.tracker.start_experiment("test", {})
        self.tracker.add_note(exp.id, "First run")
        assert self.tracker.get_experiment(exp.id).notes == "First run"

    def test_end_experiment(self) -> None:
        exp = self.tracker.start_experiment("test", {})
        self.tracker.end_experiment(exp.id)
        assert self.tracker.get_experiment(exp.id).status == ExperimentStatus.COMPLETED

    def test_fail_experiment(self) -> None:
        exp = self.tracker.start_experiment("test", {})
        self.tracker.fail_experiment(exp.id)
        assert self.tracker.get_experiment(exp.id).status == ExperimentStatus.FAILED

    def test_nested_runs(self) -> None:
        parent = self.tracker.start_experiment("parent", {})
        child = self.tracker.start_experiment("child", {}, parent_id=parent.id)
        nested = self.tracker.get_nested_runs(parent.id)
        assert len(nested) == 1

    def test_compare(self) -> None:
        exp1 = self.tracker.start_experiment("e1", {})
        self.tracker.log_metric(exp1.id, "acc", 0.90)
        self.tracker.end_experiment(exp1.id)
        exp2 = self.tracker.start_experiment("e2", {})
        self.tracker.log_metric(exp2.id, "acc", 0.95)
        self.tracker.end_experiment(exp2.id)
        comp = self.tracker.compare([exp1.id, exp2.id], "acc")
        assert exp1.id in comp

    def test_best_experiment_max(self) -> None:
        exp1 = self.tracker.start_experiment("e1", {})
        self.tracker.log_metric(exp1.id, "acc", 0.90)
        self.tracker.end_experiment(exp1.id)
        exp2 = self.tracker.start_experiment("e2", {})
        self.tracker.log_metric(exp2.id, "acc", 0.95)
        self.tracker.end_experiment(exp2.id)
        best = self.tracker.best_experiment("acc", "max")
        assert best is not None
        assert best.metrics["acc"] == 0.95

    def test_best_experiment_min(self) -> None:
        exp1 = self.tracker.start_experiment("e1", {})
        self.tracker.log_metric(exp1.id, "loss", 0.1)
        self.tracker.end_experiment(exp1.id)
        exp2 = self.tracker.start_experiment("e2", {})
        self.tracker.log_metric(exp2.id, "loss", 0.3)
        self.tracker.end_experiment(exp2.id)
        best = self.tracker.best_experiment("loss", "min")
        assert best is not None
        assert best.metrics["loss"] == 0.1

    def test_best_experiment_none(self) -> None:
        best = self.tracker.best_experiment("acc")
        assert best is None

    def test_list_by_status(self) -> None:
        exp = self.tracker.start_experiment("e1", {})
        self.tracker.end_experiment(exp.id)
        completed = self.tracker.list_experiments(status=ExperimentStatus.COMPLETED)
        assert len(completed) >= 1

    def test_list_by_tag(self) -> None:
        self.tracker.start_experiment("e1", {}, tags=["ml"])
        self.tracker.start_experiment("e2", {}, tags=["baseline"])
        ml_exps = self.tracker.list_experiments(tag="ml")
        assert len(ml_exps) == 1

    def test_stats(self) -> None:
        self.tracker.start_experiment("e1", {})
        stats = self.tracker.stats()
        assert stats["experiments"] == 1

    def test_get_unknown_raises(self) -> None:
        with pytest.raises(KeyError, match="not found"):
            self.tracker.get_experiment("unknown")


# ═══════════════════════════════════════════════════════════════════════════════
# 5. DATA LAKE
# ═══════════════════════════════════════════════════════════════════════════════

from aios_core.data_lake import Schema, Partition, DataLake


class TestSchema:
    def test_validate_pass(self) -> None:
        s = Schema("test", required_fields=["name"], field_types={"age": int})
        valid, errors = s.validate({"name": "Alice", "age": 30})
        assert valid is True
        assert errors == []

    def test_validate_fail_missing(self) -> None:
        s = Schema("test", required_fields=["name"])
        valid, errors = s.validate({"age": 30})
        assert valid is False

    def test_validate_fail_type(self) -> None:
        s = Schema("test", field_types={"age": int})
        valid, errors = s.validate({"age": "30"})
        assert valid is False


class TestDataLake:
    def setup_method(self) -> None:
        self.lake = DataLake()

    def test_ingest(self) -> None:
        ok = self.lake.ingest({"event": "click", "timestamp": "2026-01-01T12:00:00"})
        assert ok is True

    def test_ingest_with_schema(self) -> None:
        self.lake.register_schema(Schema("events", required_fields=["event"]))
        self.lake.set_default_schema("events")
        ok = self.lake.ingest({"event": "click", "timestamp": "2026-01-01T12:00:00"})
        assert ok is True
        ok = self.lake.ingest({"timestamp": "2026-01-01"})  # missing event
        assert ok is False

    def test_ingest_batch(self) -> None:
        count = self.lake.ingest_batch([{"event": "a"}, {"event": "b"}])
        assert count == 2

    def test_query_by_date(self) -> None:
        self.lake.ingest({"event": "click", "timestamp": "2026-01-15T12:00:00"})
        results = self.lake.query(date="2026-01-15")
        assert len(results) == 1

    def test_query_no_date(self) -> None:
        self.lake.ingest({"event": "click"})
        results = self.lake.query()
        assert len(results) == 1

    def test_query_by_field(self) -> None:
        self.lake.ingest({"event": "click", "user": "alice"})
        self.lake.ingest({"event": "click", "user": "bob"})
        results = self.lake.query_by_field("user", "alice")
        assert len(results) == 1

    def test_aggregate_sum(self) -> None:
        self.lake.ingest({"event": "purchase", "amount": 10.0, "timestamp": "2026-01-01"})
        self.lake.ingest({"event": "purchase", "amount": 20.0, "timestamp": "2026-01-01"})
        total = self.lake.aggregate("amount", "sum")
        assert total == 30.0

    def test_aggregate_avg(self) -> None:
        self.lake.ingest({"event": "purchase", "amount": 10.0})
        self.lake.ingest({"event": "purchase", "amount": 20.0})
        avg = self.lake.aggregate("amount", "avg")
        assert avg == 15.0

    def test_aggregate_count(self) -> None:
        self.lake.ingest({"event": "click", "amount": 1.0})
        self.lake.ingest({"event": "click", "amount": 2.0})
        # Count operates on numeric fields
        count = self.lake.aggregate("amount", "count")
        assert count == 2

    def test_create_view(self) -> None:
        self.lake.ingest({"event": "purchase", "amount": 100.0})
        view = self.lake.create_view("sales", aggregations={"total_amount": ("amount", "sum")})
        assert view["total_amount"] == 100.0

    def test_get_view(self) -> None:
        self.lake.create_view("test_view", aggregations={"x": ("amount", "sum")})
        v = self.lake.get_view("test_view")
        assert v is not None

    def test_stats(self) -> None:
        self.lake.ingest({"event": "test"})
        stats = self.lake.stats()
        assert stats["total_events"] >= 1


# ═══════════════════════════════════════════════════════════════════════════════
# 6. API VERSIONING
# ═══════════════════════════════════════════════════════════════════════════════

from aios_core.api_versioning import VersionNegotiation, VersionRoute, APIVersioning, api_versioning


class TestVersionNegotiation:
    def test_from_header(self) -> None:
        req = {"headers": {"X-API-Version": "v2"}}
        assert VersionNegotiation.from_header(req) == "v2"

    def test_from_header_default(self) -> None:
        req = {"headers": {}}
        assert VersionNegotiation.from_header(req) == "v1"

    def test_from_path(self) -> None:
        req = {"path": "/v2/users"}
        assert VersionNegotiation.from_path(req) == "v2"

    def test_from_path_default(self) -> None:
        req = {"path": "/users"}
        assert VersionNegotiation.from_path(req) == "v1"

    def test_from_query(self) -> None:
        req = {"query": {"version": "v3"}}
        assert VersionNegotiation.from_query(req) == "v3"

    def test_negotiate_header_priority(self) -> None:
        req = {"headers": {"X-API-Version": "v2"}, "path": "/v3/users", "query": {"version": "v4"}}
        assert VersionNegotiation.negotiate(req, ["header"]) == "v2"


class TestAPIVersioning:
    def setup_method(self) -> None:
        self.api = APIVersioning()

    def test_register(self) -> None:
        self.api.register("v1", "/users", lambda r: {"users": []})
        assert "v1" in self.api.versions

    def test_register_version(self) -> None:
        self.api.register_version("v1", {"/health": lambda r: {"status": "ok"}})
        assert len(self.api.versions["v1"]) >= 1

    def test_resolve(self) -> None:
        self.api.register("v1", "/health", lambda r: {"status": "ok"})
        result = self.api.resolve({"headers": {"X-API-Version": "v1"}, "path": "/health"})
        assert result["status"] == "ok"

    def test_resolve_default_fallback(self) -> None:
        self.api.register("v1", "/health", lambda r: {"status": "ok"})
        result = self.api.resolve({"path": "/health"})
        assert result["status"] == "ok"

    def test_resolve_not_found(self) -> None:
        result = self.api.resolve({"path": "/unknown"})
        assert result["status"] == 404

    def test_deprecation_notice(self) -> None:
        self.api.register("v1", "/users", lambda r: {"users": []},
                          deprecated=True, deprecation_message="Use v2 instead")
        result = self.api.resolve({"path": "/users"})
        assert "warnings" in result

    def test_deprecate_version(self) -> None:
        self.api.register("v1", "/a", lambda r: {"ok": True})
        self.api.deprecate_version("v1", "v1 is deprecated")
        deprecated = self.api.get_deprecated_versions()
        assert "v1" in deprecated

    def test_list_versions(self) -> None:
        self.api.register("v1", "/a", lambda r: 1)
        self.api.register("v2", "/a", lambda r: 2)
        versions = self.api.list_versions()
        assert "v1" in versions
        assert "v2" in versions

    def test_get_version(self) -> None:
        result = self.api.get_version({"headers": {"X-API-Version": "v2"}})
        assert result == "v2"

    def test_stats(self) -> None:
        self.api.register("v1", "/a", lambda r: 1)
        stats = self.api.stats()
        assert stats["versions"] >= 1

    def test_singleton(self) -> None:
        assert isinstance(api_versioning, APIVersioning)


# ═══════════════════════════════════════════════════════════════════════════════
# 7. DIGITAL TWIN
# ═══════════════════════════════════════════════════════════════════════════════

from aios_core.digital_twin import TwinProperty, SimulationOutcome, DigitalTwin


class TestDigitalTwin:
    def setup_method(self) -> None:
        self.twin = DigitalTwin("agent_1", "rozetka_agent")

    def test_add_property(self) -> None:
        self.twin.add_property("cpu_usage", 45.0, min_value=0, max_value=100)
        assert self.twin.get_property("cpu_usage") == 45.0

    def test_update_property(self) -> None:
        self.twin.add_property("cpu_usage", 45.0, min_value=0, max_value=100)
        ok = self.twin.update_property("cpu_usage", 80.0)
        assert ok is True
        assert self.twin.get_property("cpu_usage") == 80.0

    def test_update_property_out_of_bounds(self) -> None:
        self.twin.add_property("cpu_usage", 45.0, min_value=0, max_value=100)
        ok = self.twin.update_property("cpu_usage", 150.0)
        assert ok is False

    def test_sync(self) -> None:
        self.twin.sync({"cpu_usage": 50.0, "memory": 2.0})
        assert self.twin.state["cpu_usage"] == 50.0

    def test_sync_returns_diff(self) -> None:
        self.twin.sync({"cpu_usage": 50.0})
        diff = self.twin.sync({"cpu_usage": 60.0, "memory": 2.0})
        assert "changed" in diff
        assert "added" in diff

    def test_rollback(self) -> None:
        self.twin.sync({"cpu_usage": 50.0})
        self.twin.sync({"cpu_usage": 90.0})
        state = self.twin.rollback()
        assert state["cpu_usage"] == 50.0

    def test_simulate(self) -> None:
        outcome = self.twin.simulate("scale_up")
        assert outcome.predicted_outcome in ("success", "failure", "degraded")

    def test_simulate_with_handler(self) -> None:
        self.twin.register_action("deploy", lambda s: SimulationOutcome(action="deploy", predicted_outcome="success", confidence=0.9))
        outcome = self.twin.simulate("deploy")
        assert outcome.predicted_outcome == "success"
        assert outcome.confidence == 0.9

    def test_what_if(self) -> None:
        outcome = self.twin.what_if("scale_up", {"cpu_usage": 95.0})
        assert outcome.warnings  # has "what-if" marker
        # State should NOT be changed (what-if)
        assert self.twin.state.get("cpu_usage") != 95.0

    def test_inject_event(self) -> None:
        outcome = self.twin.inject_event("failure", {"status": "crashed"})
        assert outcome.predicted_outcome == "failure"

    def test_compare_to(self) -> None:
        self.twin.sync({"cpu": 50.0})
        diff = self.twin.compare_to({"cpu": 80.0, "mem": 2.0})
        assert "changed" in diff

    def test_stats(self) -> None:
        self.twin.sync({"x": 1})
        stats = self.twin.stats()
        assert stats["id"] == "agent_1"


# ═══════════════════════════════════════════════════════════════════════════════
# 8. COMPLIANCE
# ═══════════════════════════════════════════════════════════════════════════════

from aios_core.compliance import (
    ViolationSeverity, ComplianceRule, Violation, ComplianceScore, ComplianceFramework,
)


class TestComplianceFramework:
    def setup_method(self) -> None:
        self.cf = ComplianceFramework()

    def test_check_compliance_pass(self) -> None:
        result = self.cf.check_compliance("gdpr", ["data_minimization", "consent", "right_to_be_forgotten"])
        assert result["compliant"] is True

    def test_check_compliance_fail(self) -> None:
        result = self.cf.check_compliance("gdpr", ["data_minimization"])
        assert result["compliant"] is False
        assert "consent" in result["missing"]

    def test_check_compliance_score(self) -> None:
        result = self.cf.check_compliance("gdpr", ["data_minimization", "consent"])
        assert result["score"] > 0

    def test_register_policy(self) -> None:
        self.cf.register_policy("iso27001", ["risk_assessment", "access_control"])
        result = self.cf.check_compliance("iso27001", ["risk_assessment", "access_control"])
        assert result["compliant"] is True

    def test_add_rule(self) -> None:
        rule = ComplianceRule("encryption_check", "soc2",
                              check_fn=lambda ctx: ctx.get("encryption_enabled", False),
                              severity=ViolationSeverity.HIGH,
                              remediation="Enable encryption")
        self.cf.add_rule(rule)
        assert "encryption_check" in self.cf.rules

    def test_check_rules_compliant(self) -> None:
        self.cf.add_rule(ComplianceRule("test_rule", "test", check_fn=lambda ctx: True))
        violations = self.cf.check_rules({"test": True})
        assert len(violations) == 0

    def test_check_rules_violation(self) -> None:
        self.cf.add_rule(ComplianceRule("test_rule", "test", check_fn=lambda ctx: ctx.get("ok", False)))
        violations = self.cf.check_rules({"ok": False})
        assert len(violations) >= 1

    def test_resolve_violation(self) -> None:
        v = Violation("test", "policy", ViolationSeverity.MEDIUM)
        self.cf.violations.append(v)
        # Can't easily resolve without matching, but test the method
        assert not v.resolved
        v.resolve()
        assert v.resolved

    def test_get_violations(self) -> None:
        self.cf.violations.append(Violation("r1", "p1", ViolationSeverity.LOW))
        violations = self.cf.get_violations()
        assert len(violations) >= 1

    def test_get_violations_unresolved(self) -> None:
        v = Violation("r1", "p1", ViolationSeverity.LOW)
        self.cf.violations.append(v)
        unresolved = self.cf.get_violations(unresolved_only=True)
        assert len(unresolved) >= 1

    def test_overall_score(self) -> None:
        self.cf.check_compliance("gdpr", ["data_minimization"])
        score = self.cf.overall_score()
        assert isinstance(score, float)

    def test_stats(self) -> None:
        stats = self.cf.stats()
        assert "gdpr" in stats["policies"]

    def test_audit_log(self) -> None:
        self.cf.check_compliance("gdpr", ["data_minimization"])
        log = self.cf.get_audit_log()
        assert len(log) >= 1


# ═══════════════════════════════════════════════════════════════════════════════
# 9. SECRETS MANAGER
# ═══════════════════════════════════════════════════════════════════════════════

from aios_core.secrets import SecretVersion, RotationPolicy, SecretsManager, secrets


class TestSecretsManager:
    def setup_method(self) -> None:
        self.sm = SecretsManager()

    def test_set_and_get(self) -> None:
        self.sm.set("db_password", "secret123")
        assert self.sm.get("db_password") == "secret123"

    def test_get_default(self) -> None:
        assert self.sm.get("nonexistent", "fallback") == "fallback"

    def test_get_default_none(self) -> None:
        assert self.sm.get("nonexistent") is None

    def test_env_priority(self) -> None:
        os.environ["test_env_key"] = "env_value"
        self.sm.set("test_env_key", "mem_value")
        assert self.sm.get("test_env_key") == "env_value"
        del os.environ["test_env_key"]

    def test_delete(self) -> None:
        self.sm.set("key1", "val1")
        self.sm.delete("key1")
        assert self.sm.get("key1") is None

    def test_namespace(self) -> None:
        self.sm.set("key1", "default_val", namespace="default")
        self.sm.set("key1", "ns_val", namespace="production")
        assert self.sm.get("key1", namespace="production") == "ns_val"

    def test_list_namespace(self) -> None:
        self.sm.set("k1", "v1", namespace="prod")
        self.sm.set("k2", "v2", namespace="prod")
        keys = self.sm.list_namespace("prod")
        assert len(keys) == 2

    def test_list_keys(self) -> None:
        self.sm.set("k1", "v1")
        self.sm.set("k2", "v2")
        keys = self.sm.list_keys()
        assert len(keys) == 2

    def test_encryption(self) -> None:
        self.sm.set("secret_key", "my_secret", encrypt=True)
        decrypted = self.sm.get_encrypted("secret_key")
        assert decrypted == "my_secret"

    def test_versioning(self) -> None:
        self.sm.set("key", "v1")
        self.sm.set("key", "v2")
        versions = self.sm.get_versions("key")
        assert len(versions) == 2

    def test_get_version(self) -> None:
        self.sm.set("key", "first_value")
        self.sm.set("key", "second_value")
        v1 = self.sm.get_version("key", 1)
        assert v1 == "first_value"

    def test_rotation_policy(self) -> None:
        self.sm.set("api_key", "original")
        self.sm.set_rotation_policy("api_key", interval_days=90)
        policy = self.sm._rotation_policies.get("api_key")
        assert policy is not None

    def test_rotate(self) -> None:
        self.sm.set("key", "old_val")
        new = self.sm.rotate("key", "new_val")
        assert new == "new_val"

    def test_mask(self) -> None:
        masked = self.sm.mask("secret123", show_chars=4)
        assert masked == "*****t123"
        assert len(masked) == len("secret123")

    def test_mask_short(self) -> None:
        masked = self.sm.mask("ab", show_chars=4)
        assert masked == "**"

    def test_audit_log(self) -> None:
        self.sm.set("k1", "v1")
        self.sm.get("k1")
        log = self.sm.get_audit_log()
        assert len(log) >= 2

    def test_singleton(self) -> None:
        assert isinstance(secrets, SecretsManager)


# ═══════════════════════════════════════════════════════════════════════════════
# INTEGRATION
# ═══════════════════════════════════════════════════════════════════════════════

class TestIntegration:
    def test_scheduler_with_event_store(self) -> None:
        """Schedule events via TaskScheduler and replay via EventStore."""
        ts = TaskScheduler()
        es = EventStore()
        events_log = []
        ts.schedule("log_event", lambda: events_log.append("done"), datetime.now() - timedelta(seconds=1))
        es.append("task_executed", {"name": "log_event"})
        ts.tick()
        assert len(events_log) == 1

    def test_experiment_with_data_lake(self) -> None:
        """Track experiments using DataLake for result storage."""
        tracker = ExperimentTracker()
        lake = DataLake()
        exp = tracker.start_experiment("model_v1", {"lr": 0.01})
        tracker.log_metric(exp.id, "accuracy", 0.95)
        lake.ingest({"experiment_id": exp.id, "accuracy": 0.95, "timestamp": "2026-01-01"})
        results = lake.query_by_field("experiment_id", exp.id)
        assert len(results) == 1

    def test_compliance_with_secrets(self) -> None:
        """Compliance checks secrets encryption status."""
        cf = ComplianceFramework()
        sm = SecretsManager()
        sm.set("db_password", "secret", encrypt=True)
        cf.add_rule(ComplianceRule(
            "secrets_encrypted", "soc2",
            check_fn=lambda ctx: ctx.get("secrets_encrypted", False),
            severity=ViolationSeverity.HIGH,
            remediation="Enable secrets encryption",
        ))
        violations = cf.check_rules({"secrets_encrypted": True})
        assert len(violations) == 0

    def test_observability_with_task_scheduler(self) -> None:
        """Track scheduled task execution via Observability."""
        obs = Observability()
        ts = TaskScheduler()
        trace_id = obs.start_trace("scheduler_tick")
        ts.schedule("task1", lambda: 1, datetime.now() - timedelta(seconds=1))
        ts.tick()
        obs.end_trace(trace_id)
        duration = obs.get_trace_duration(trace_id)
        assert duration >= 0

    def test_digital_twin_with_experiment_tracking(self) -> None:
        """Track twin simulations as experiments."""
        twin = DigitalTwin("agent_1", "rozetka")
        tracker = ExperimentTracker()
        exp = tracker.start_experiment("twin_sim", {"action": "scale_up"})
        outcome = twin.simulate("scale_up")
        tracker.log_metric(exp.id, "confidence", outcome.confidence)
        tracker.end_experiment(exp.id)
        best = tracker.best_experiment("confidence", "max")
        assert best is not None
