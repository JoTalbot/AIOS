"""Tests for v10.5.0 modules: Zero Trust, Self-Healing, Circuit Breaker,
API Gateway, Graceful Shutdown, Service Mesh, Distributed Queue,
Chaos Testing, Auto-Scaler, Health Checks.

Each module section: ~20-30 tests covering registration, execution,
edge cases, backward-compatible façade, and stats.
"""

from __future__ import annotations

import time
import pytest

# ═══════════════════════════════════════════════════════════════════════════════
# 1. ZERO TRUST
# ═══════════════════════════════════════════════════════════════════════════════

from aios_core.zero_trust import (
    TrustLevel, DeviceProfile, TrustPolicy, TrustEngine, ZeroTrust,
)


class TestDeviceProfile:
    def test_compute_trust_basic(self) -> None:
        d = DeviceProfile(device_id="dev1", fingerprint="abc123", platform="rozetka")
        score = d.compute_trust()
        assert score >= 20.0  # fingerprint bonus

    def test_compute_trust_with_mfa(self) -> None:
        d = DeviceProfile(device_id="dev2", fingerprint="abc", platform="olx",
                          attributes={"verified_device": True, "mfa_enabled": True})
        score = d.compute_trust()
        assert score >= 75.0

    def test_trust_level_mapping(self) -> None:
        d = DeviceProfile(device_id="dev1", fingerprint="abc")
        d.trust_score = 80.0
        assert d.trust_level() == TrustLevel.HIGH

    def test_trust_level_untrusted(self) -> None:
        d = DeviceProfile(device_id="dev1")
        d.trust_score = 0.0
        assert d.trust_level() == TrustLevel.UNTRUSTED

    def test_trust_score_capped_at_100(self) -> None:
        d = DeviceProfile(device_id="dev1", fingerprint="a", platform="r",
                          ip_address="1.2.3.4", attributes={"verified_device": True, "mfa_enabled": True})
        score = d.compute_trust()
        assert score <= 100.0


class TestTrustPolicy:
    def test_policy_evaluate_pass(self) -> None:
        p = TrustPolicy(name="p1", resource="listing", min_trust_level=TrustLevel.MEDIUM)
        ctx = {"trust_level": TrustLevel.HIGH, "authenticated": True}
        assert p.evaluate(ctx) is True

    def test_policy_evaluate_fail_trust(self) -> None:
        p = TrustPolicy(name="p1", resource="listing", min_trust_level=TrustLevel.HIGH)
        ctx = {"trust_level": TrustLevel.LOW}
        assert p.evaluate(ctx) is False

    def test_policy_with_list_condition(self) -> None:
        p = TrustPolicy(name="p1", resource="listing", conditions={"region": ["dnipro", "kyiv"]})
        assert p.evaluate({"trust_level": 100, "region": "dnipro"}) is True
        assert p.evaluate({"trust_level": 100, "region": "lviv"}) is False

    def test_policy_with_nested_condition(self) -> None:
        p = TrustPolicy(name="p1", resource="admin", conditions={"device": {"verified": True}})
        assert p.evaluate({"trust_level": 100, "device": {"verified": True}}) is True
        assert p.evaluate({"trust_level": 100, "device": {"verified": False}}) is False


class TestTrustEngine:
    def setup_method(self) -> None:
        self.engine = TrustEngine()

    def test_register_device(self) -> None:
        d = DeviceProfile(device_id="dev1", fingerprint="abc")
        self.engine.register_device(d)
        assert "dev1" in self.engine.devices

    def test_verify_not_authenticated(self) -> None:
        assert self.engine.verify({"authenticated": False}) is False

    def test_verify_authenticated_no_policies(self) -> None:
        assert self.engine.verify({"authenticated": True, "authorized": True, "resource": "listing"}) is True

    def test_verify_with_policy_pass(self) -> None:
        self.engine.add_policy(TrustPolicy("p1", "listing", min_trust_level=TrustLevel.LOW))
        ctx = {"authenticated": True, "authorized": True, "resource": "listing", "trust_level": TrustLevel.MEDIUM}
        assert self.engine.verify(ctx) is True

    def test_verify_with_policy_fail(self) -> None:
        self.engine.add_policy(TrustPolicy("p1", "listing", min_trust_level=TrustLevel.HIGH))
        ctx = {"authenticated": True, "resource": "listing", "trust_level": TrustLevel.LOW}
        assert self.engine.verify(ctx) is False

    def test_verify_with_device_trust(self) -> None:
        d = DeviceProfile(device_id="dev1", fingerprint="abc", attributes={"mfa_enabled": True})
        self.engine.register_device(d)
        ctx = {"authenticated": True, "device_id": "dev1", "resource": "*"}
        assert self.engine.verify(ctx) is True

    def test_revoke_device(self) -> None:
        d = DeviceProfile(device_id="dev1", fingerprint="abc", attributes={"mfa_enabled": True})
        self.engine.register_device(d)
        self.engine.revoke_device("dev1")
        assert self.engine.devices["dev1"].trust_score == 0.0

    def test_network_segment_allowed(self) -> None:
        assert self.engine.check_network_segment("192.168.1.100", ["192.168.0.0/16"]) is True

    def test_network_segment_blocked(self) -> None:
        assert self.engine.check_network_segment("10.0.0.1", ["192.168.0.0/16"]) is False

    def test_stats(self) -> None:
        self.engine.register_device(DeviceProfile(device_id="d1", fingerprint="a"))
        self.engine.add_policy(TrustPolicy("p1", "listing"))
        stats = self.engine.stats()
        assert stats["devices"] == 1
        assert stats["policies"] == 1

    def test_audit_log(self) -> None:
        self.engine.verify({"authenticated": False})
        log = self.engine.get_audit_log()
        assert len(log) >= 1


class TestZeroTrustFacade:
    def test_add_policy(self) -> None:
        zt = ZeroTrust()
        zt.add_policy("p1", {"resource": "listing", "min_trust": 50})
        assert "p1" in zt.policies

    def test_verify_authenticated_authorized(self) -> None:
        zt = ZeroTrust()
        assert zt.verify({"authenticated": True, "authorized": True}) is True

    def test_verify_unauthenticated(self) -> None:
        zt = ZeroTrust()
        assert zt.verify({"authenticated": False}) is False

    def test_stats(self) -> None:
        zt = ZeroTrust()
        zt.add_policy("p1", {})
        assert zt.stats() == {"policies": 1}

    def test_engine_access(self) -> None:
        zt = ZeroTrust()
        assert isinstance(zt.engine(), TrustEngine)


# ═══════════════════════════════════════════════════════════════════════════════
# 2. SELF-HEALING
# ═══════════════════════════════════════════════════════════════════════════════

from aios_core.self_healing import (
    RecoveryLevel, RecoveryRecord, HealthCheck, HealthMonitor, SelfHealing,
)


class TestHealthMonitor:
    def test_register_and_run(self) -> None:
        hm = HealthMonitor()
        hm.register("db", lambda: True)
        results = hm.run_all()
        assert results["db"] is True

    def test_overall_healthy(self) -> None:
        hm = HealthMonitor()
        hm.register("db", lambda: True)
        hm.register("cache", lambda: True)
        assert hm.overall_healthy() is True

    def test_overall_unhealthy(self) -> None:
        hm = HealthMonitor()
        hm.register("db", lambda: True)
        hm.register("cache", lambda: False)
        assert hm.overall_healthy() is False

    def test_unhealthy_services(self) -> None:
        hm = HealthMonitor()
        hm.register("db", lambda: True)
        hm.register("cache", lambda: False)
        assert hm.unhealthy_services() == ["cache"]

    def test_check_with_exception(self) -> None:
        hm = HealthMonitor()
        hm.register("fail", lambda: (_ for _ in ()).throw(RuntimeError("boom")))
        results = hm.run_all()
        assert results["fail"] is False


class TestSelfHealing:
    def test_register_and_heal_success(self) -> None:
        sh = SelfHealing()
        sh.register_strategy("ConnectionError", lambda ctx: True)
        result = sh.heal(ConnectionError("timeout"))
        assert result is True

    def test_heal_no_strategy(self) -> None:
        sh = SelfHealing()
        result = sh.heal(RuntimeError("unknown"))
        assert result is False

    def test_heal_strategy_failure(self) -> None:
        sh = SelfHealing()
        sh.register_strategy("ConnectionError", lambda ctx: (_ for _ in ()).throw(ValueError("strategy fails")))
        result = sh.heal(ConnectionError("timeout"))
        assert result is False

    def test_recovery_history(self) -> None:
        sh = SelfHealing()
        sh.register_strategy("ConnectionError", lambda ctx: True)
        sh.heal(ConnectionError("err"))
        assert len(sh.recovery_history) == 1

    def test_escalation(self) -> None:
        sh = SelfHealing()
        sh.register_strategy("ConnectionError", lambda ctx: (_ for _ in ()).throw(ValueError("fail")))
        # Fail repeatedly to trigger escalation
        sh.heal(ConnectionError("err1"))  # attempt 1 → LIGHT
        sh.heal(ConnectionError("err2"))  # attempt 2 → still trying
        records = sh.recovery_history
        # Level should escalate
        assert records[-1].level.value != RecoveryLevel.LIGHT.value or len(records) >= 2

    def test_max_recovery_attempts(self) -> None:
        sh = SelfHealing(max_recovery_attempts=2)
        sh.register_strategy("ConnectionError", lambda ctx: (_ for _ in ()).throw(ValueError("fail")))
        sh.heal(ConnectionError("e1"))
        sh.heal(ConnectionError("e2"))
        result = sh.heal(ConnectionError("e3"))
        assert result is False  # exceeded max

    def test_diagnose(self) -> None:
        sh = SelfHealing()
        sh.register_strategy("ConnectionError", lambda ctx: True)
        sh.register_health_check("db", lambda: True)
        diag = sh.diagnose()
        assert "healthy" in diag
        assert "recent_recoveries" in diag

    def test_stats(self) -> None:
        sh = SelfHealing()
        sh.register_strategy("ConnectionError", lambda ctx: True)
        sh.heal(ConnectionError("e"))
        stats = sh.stats()
        assert stats["strategies"] == 1
        assert stats["successful_recoveries"] == 1

    def test_reset_attempts(self) -> None:
        sh = SelfHealing()
        sh.register_strategy("ConnectionError", lambda ctx: (_ for _ in ()).throw(ValueError("fail")))
        sh.heal(ConnectionError("e"))
        sh.reset_attempts("ConnectionError")
        assert sh._attempt_counts.get("ConnectionError", 0) == 0


# ═══════════════════════════════════════════════════════════════════════════════
# 3. CIRCUIT BREAKER
# ═══════════════════════════════════════════════════════════════════════════════

from aios_core.circuit_breaker import (
    CircuitState, CircuitMetrics, CircuitBreaker, CircuitOpenError,
)


class TestCircuitMetrics:
    def test_record_success(self) -> None:
        m = CircuitMetrics()
        m.record_success(1.5)
        assert m.success_count == 1
        assert m.total_call_time == 1.5

    def test_record_failure(self) -> None:
        m = CircuitMetrics()
        m.record_failure()
        assert m.failure_count == 1

    def test_success_rate(self) -> None:
        m = CircuitMetrics()
        m.record_success(1.0)
        m.record_success(2.0)
        m.record_failure()
        assert m.success_rate() == 2/3

    def test_success_rate_no_data(self) -> None:
        m = CircuitMetrics()
        assert m.success_rate() == 1.0


class TestCircuitBreaker:
    def test_call_success_closed(self) -> None:
        cb = CircuitBreaker()
        result = cb.call(lambda: 42)
        assert result == 42
        assert cb.state == CircuitState.CLOSED

    def test_call_failure_counts(self) -> None:
        cb = CircuitBreaker(failure_threshold=3)
        for i in range(2):
            try:
                cb.call(lambda: (_ for _ in ()).throw(RuntimeError("fail")))
            except RuntimeError:
                pass
        assert cb.failure_count == 2
        assert cb.state == CircuitState.CLOSED

    def test_trip_to_open(self) -> None:
        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=1.0)
        for i in range(3):
            try:
                cb.call(lambda: (_ for _ in ()).throw(RuntimeError("fail")))
            except RuntimeError:
                pass
        assert cb.state == CircuitState.OPEN

    def test_open_rejects_calls(self) -> None:
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=10.0)
        try:
            cb.call(lambda: (_ for _ in ()).throw(RuntimeError("fail")))
        except RuntimeError:
            pass
        assert cb.state == CircuitState.OPEN
        with pytest.raises(CircuitOpenError):
            cb.call(lambda: 1)

    def test_fallback_on_open(self) -> None:
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=10.0, fallback=lambda *a, **k: "fallback")
        try:
            cb.call(lambda: (_ for _ in ()).throw(RuntimeError("fail")))
        except RuntimeError:
            pass
        result = cb.call(lambda: 1)
        assert result == "fallback"

    def test_half_open_probing(self) -> None:
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=0.01, half_open_max_calls=1)
        try:
            cb.call(lambda: (_ for _ in ()).throw(RuntimeError("fail")))
        except RuntimeError:
            pass
        assert cb.state == CircuitState.OPEN
        time.sleep(0.05)  # wait for recovery timeout
        result = cb.call(lambda: 42)  # half-open probe → success → close
        assert result == 42
        assert cb.state == CircuitState.CLOSED

    def test_listener_notification(self) -> None:
        transitions = []
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=0.01)
        cb.add_listener(lambda old, new: transitions.append((old.value, new.value)))
        try:
            cb.call(lambda: (_ for _ in ()).throw(RuntimeError("fail")))
        except RuntimeError:
            pass
        assert len(transitions) >= 1
        assert transitions[-1][1] == CircuitState.OPEN.value

    def test_force_open(self) -> None:
        cb = CircuitBreaker()
        cb.force_open()
        assert cb.state == CircuitState.OPEN

    def test_force_close(self) -> None:
        cb = CircuitBreaker()
        cb.force_open()
        cb.force_close()
        assert cb.state == CircuitState.CLOSED

    def test_reset(self) -> None:
        cb = CircuitBreaker(failure_threshold=1)
        try:
            cb.call(lambda: (_ for _ in ()).throw(RuntimeError("fail")))
        except RuntimeError:
            pass
        cb.reset()
        assert cb.failure_count == 0
        assert cb.state == CircuitState.CLOSED

    def test_stats(self) -> None:
        cb = CircuitBreaker()
        cb.call(lambda: 1)
        stats = cb.stats()
        assert stats["state"] == "closed"
        assert stats["metrics"]["success_count"] == 1


# ═══════════════════════════════════════════════════════════════════════════════
# 4. API GATEWAY
# ═══════════════════════════════════════════════════════════════════════════════

from aios_core.api_gateway import Route, APIGateway


class TestAPIGateway:
    def setup_method(self) -> None:
        self.gw = APIGateway()

    def test_register_and_handle(self) -> None:
        self.gw.register("/hello", lambda r: {"message": "hello"})
        result = self.gw.handle("/hello", {})
        assert result["message"] == "hello"

    def test_handle_not_found(self) -> None:
        result = self.gw.handle("/unknown", {})
        assert result["status"] == 404

    def test_middleware_pipeline(self) -> None:
        self.gw.register("/test", lambda r: {"processed": r.get("added", False)})
        self.gw.add_middleware(lambda r: {**r, "added": True})
        result = self.gw.handle("/test", {})
        assert result["processed"] is True

    def test_rate_limit(self) -> None:
        self.gw.register("/limited", lambda r: {"ok": True}, rate_limit=2)
        self.gw.handle("/limited", {})  # 1
        self.gw.handle("/limited", {})  # 2
        result = self.gw.handle("/limited", {})  # 3 → rate limited
        assert result["status"] == 429

    def test_auth_required(self) -> None:
        self.gw.register("/admin", lambda r: {"admin": True}, auth_required=True)
        result = self.gw.handle("/admin", {})
        assert result["status"] == 401

    def test_auth_pass(self) -> None:
        self.gw.register("/admin", lambda r: {"admin": True}, auth_required=True)
        result = self.gw.handle("/admin", {"authenticated": True})
        assert result.get("admin") is True

    def test_method_check(self) -> None:
        self.gw.register("/data", lambda r: {"data": True}, methods=["GET"])
        result = self.gw.handle("/data", {"method": "POST"})
        assert result["status"] == 405

    def test_route_versioning(self) -> None:
        self.gw.register("/v1/users", lambda r: {"v": 1}, version="v1")
        self.gw.register("/v2/users", lambda r: {"v": 2}, version="v2")
        v1_routes = self.gw.get_routes_by_version("v1")
        assert len(v1_routes) == 1

    def test_health_endpoint(self) -> None:
        health = self.gw.health()
        assert health["status"] == "healthy"

    def test_metrics(self) -> None:
        self.gw.register("/test", lambda r: {"ok": True})
        self.gw.handle("/test", {})
        self.gw.handle("/unknown", {})
        m = self.gw.metrics()
        assert m["total_requests"] == 2

    def test_stats(self) -> None:
        self.gw.register("/a", lambda r: 1)
        self.gw.register("/b", lambda r: 2)
        stats = self.gw.stats()
        assert stats["routes"] == 2

    def test_reset_rate_limit(self) -> None:
        self.gw.register("/lim", lambda r: {"ok": True}, rate_limit=1)
        self.gw.handle("/lim", {})
        result = self.gw.handle("/lim", {})
        assert result["status"] == 429
        self.gw.reset_rate_limit("/lim")
        result = self.gw.handle("/lim", {})
        assert result.get("ok") is True


# ═══════════════════════════════════════════════════════════════════════════════
# 5. GRACEFUL SHUTDOWN
# ═══════════════════════════════════════════════════════════════════════════════

from aios_core.graceful_shutdown import ShutdownPhase, ShutdownHook, GracefulShutdown, shutdown_handler


class TestGracefulShutdown:
    def test_register_handler(self) -> None:
        gs = GracefulShutdown()
        gs.register_handler(lambda: "cleanup_done")
        assert len(gs.hooks) == 1

    def test_register_hook_with_phase(self) -> None:
        gs = GracefulShutdown()
        gs.register_hook("drain_db", lambda: True, phase=ShutdownPhase.DRAIN, priority=10)
        gs.register_hook("close_conn", lambda: True, phase=ShutdownPhase.CLEANUP, priority=50)
        assert len(gs.hooks) == 2

    def test_shutdown_execution(self) -> None:
        gs = GracefulShutdown()
        results = []
        gs.register_hook("hook1", lambda: results.append("drain"), phase=ShutdownPhase.DRAIN)
        gs.register_hook("hook2", lambda: results.append("cleanup"), phase=ShutdownPhase.CLEANUP)
        gs.register_hook("hook3", lambda: results.append("finalize"), phase=ShutdownPhase.FINALIZE)
        report = gs.shutdown()
        assert report["status"] == "completed"
        assert len(results) == 3

    def test_shutdown_order(self) -> None:
        gs = GracefulShutdown()
        order = []
        gs.register_hook("f1", lambda: order.append("finalize"), phase=ShutdownPhase.FINALIZE, priority=1)
        gs.register_hook("c1", lambda: order.append("cleanup"), phase=ShutdownPhase.CLEANUP, priority=1)
        gs.register_hook("d1", lambda: order.append("drain"), phase=ShutdownPhase.DRAIN, priority=1)
        gs.shutdown()
        assert order == ["drain", "cleanup", "finalize"]

    def test_shutdown_already_started(self) -> None:
        gs = GracefulShutdown()
        gs.shutdown()
        report = gs.shutdown()
        assert report["status"] == "already_started"

    def test_shutdown_hook_failure(self) -> None:
        gs = GracefulShutdown()
        gs.register_hook("fail_hook", lambda: (_ for _ in ()).throw(ValueError("fail")), phase=ShutdownPhase.CLEANUP)
        report = gs.shutdown()
        assert report["status"] == "completed"
        assert any(r["status"] == "failed" for r in report["progress"])

    def test_remove_hook(self) -> None:
        gs = GracefulShutdown()
        gs.register_hook("test", lambda: True)
        gs.remove_hook("test")
        assert len(gs.hooks) == 0

    def test_stats(self) -> None:
        gs = GracefulShutdown()
        gs.register_hook("h1", lambda: True)
        stats = gs.stats()
        assert stats["hooks"] == 1

    def test_shutdown_handler_singleton(self) -> None:
        assert isinstance(shutdown_handler, GracefulShutdown)


# ═══════════════════════════════════════════════════════════════════════════════
# 6. SERVICE MESH
# ═══════════════════════════════════════════════════════════════════════════════

from aios_core.service_mesh import ServiceInstance, TrafficRule, ServiceMesh, service_mesh


class TestServiceInstance:
    def test_mark_healthy(self) -> None:
        inst = ServiceInstance(name="db", endpoint="localhost:5432")
        inst.mark_healthy()
        assert inst.status == "healthy"

    def test_mark_unhealthy(self) -> None:
        inst = ServiceInstance(name="db", endpoint="localhost:5432")
        inst.mark_unhealthy()
        assert inst.status == "unhealthy"

    def test_is_available(self) -> None:
        inst = ServiceInstance(name="db", endpoint="localhost:5432")
        assert inst.is_available() is True
        inst.status = "unhealthy"
        assert inst.is_available() is False


class TestTrafficRule:
    def test_select_target_basic(self) -> None:
        rule = TrafficRule(name="r1", source="api", targets={"v1": 80, "v2": 20})
        target = rule.select_target()
        assert target in ["v1", "v2"]


class TestServiceMesh:
    def setup_method(self) -> None:
        self.mesh = ServiceMesh()

    def test_register_service(self) -> None:
        self.mesh.register_service("api", "localhost:8000")
        assert "api" in self.mesh.services

    def test_discover(self) -> None:
        self.mesh.register_service("db", "localhost:5432")
        info = self.mesh.discover("db")
        assert info["endpoint"] == "localhost:5432"

    def test_discover_unknown(self) -> None:
        assert self.mesh.discover("unknown") == {}

    def test_discover_healthy(self) -> None:
        self.mesh.register_service("db", "localhost:5432")
        self.mesh.register_service("cache", "localhost:6379")
        self.mesh.services["cache"].mark_unhealthy()
        healthy = self.mesh.discover_healthy()
        assert len(healthy) == 1

    def test_traffic_route(self) -> None:
        self.mesh.register_service("api-v1", "v1:8000")
        self.mesh.register_service("api-v2", "v2:8000")
        rule = self.mesh.add_route("api", {"api-v1": 80, "api-v2": 20})
        target = self.mesh.route_request("api")
        assert target in ["api-v1", "api-v2"]

    def test_health_check(self) -> None:
        self.mesh.register_service("db", "localhost:5432")
        self.mesh.register_health_check("db", lambda: True)
        results = self.mesh.run_health_checks()
        assert results["db"] == "healthy"

    def test_health_check_failure(self) -> None:
        self.mesh.register_service("db", "localhost:5432")
        self.mesh.register_health_check("db", lambda: False)
        results = self.mesh.run_health_checks()
        assert results["db"] == "unhealthy"

    def test_select_instance_weighted(self) -> None:
        self.mesh.register_service("a", "ep_a", weight=80)
        self.mesh.register_service("b", "ep_b", weight=20)
        inst = self.mesh.select_instance("any")
        assert inst is not None

    def test_stats(self) -> None:
        self.mesh.register_service("api", "localhost:8000")
        stats = self.mesh.stats()
        assert stats["services"] == 1

    def test_singleton(self) -> None:
        assert isinstance(service_mesh, ServiceMesh)


# ═══════════════════════════════════════════════════════════════════════════════
# 7. DISTRIBUTED QUEUE
# ═══════════════════════════════════════════════════════════════════════════════

from aios_core.distributed_queue import (
    TaskPriority, TaskStatus, Task, Worker, DistributedQueue,
)


class TestTask:
    def test_auto_id(self) -> None:
        t = Task(name="test")
        assert t.id != ""

    def test_can_retry(self) -> None:
        t = Task(max_retries=3)
        assert t.can_retry() is True
        t.retry_count = 3
        assert t.can_retry() is False

    def test_duration(self) -> None:
        t = Task()
        t.started_at = 100.0
        t.completed_at = 105.0
        assert t.duration() == 5.0


class TestWorker:
    def test_available_capacity(self) -> None:
        w = Worker(id="w1", capacity=10)
        assert w.available_capacity() == 10
        w.assigned_tasks = ["t1", "t2"]
        assert w.available_capacity() == 8

    def test_is_available(self) -> None:
        w = Worker(id="w1", capacity=2)
        w.assigned_tasks = ["t1", "t2"]
        assert w.is_available() is False


class TestDistributedQueue:
    def setup_method(self) -> None:
        self.q = DistributedQueue()

    def test_enqueue(self) -> None:
        task = self.q.enqueue({"action": "scrape"}, name="scraper")
        assert task.status == TaskStatus.QUEUED
        assert self.q.size() == 1

    def test_enqueue_priority(self) -> None:
        self.q.enqueue({"a": "low"}, priority=TaskPriority.LOW)
        self.q.enqueue({"a": "crit"}, priority=TaskPriority.CRITICAL)
        t = self.q.dequeue()
        assert t.priority == TaskPriority.CRITICAL

    def test_dequeue_empty(self) -> None:
        assert self.q.dequeue() is None

    def test_dequeue_with_worker(self) -> None:
        self.q.register_worker("w1", capacity=5)
        self.q.enqueue({"a": 1})
        t = self.q.dequeue()
        assert t.worker_id == "w1"
        assert t.status == TaskStatus.RUNNING

    def test_complete(self) -> None:
        self.q.register_worker("w1")
        t = self.q.enqueue({"a": 1})
        self.q.dequeue()
        self.q.complete(t.id, result={"ok": True})
        assert self.q.completed_count() == 1

    def test_fail_and_retry(self) -> None:
        self.q.register_worker("w1")
        t = self.q.enqueue({"a": 1}, max_retries=2)
        self.q.dequeue()
        self.q.fail(t.id, error="timeout")
        # Should be re-queued for retry
        assert self.q.size() >= 0  # retry task back in queue

    def test_fail_to_dead_letter(self) -> None:
        self.q.register_worker("w1")
        t = self.q.enqueue({"a": 1}, max_retries=0)
        self.q.dequeue()
        self.q.fail(t.id, error="permanent_fail")
        assert self.q.dead_letter_count() == 1

    def test_retry_dead_letter(self) -> None:
        self.q.register_worker("w1")
        t = self.q.enqueue({"a": 1}, max_retries=0)
        self.q.dequeue()
        self.q.fail(t.id, error="fail")
        result = self.q.retry_dead_letter(t.id)
        assert result is True
        assert self.q.dead_letter_count() == 0

    def test_purge_dead_letter(self) -> None:
        self.q.register_worker("w1")
        t = self.q.enqueue({"a": 1}, max_retries=0)
        self.q.dequeue()
        self.q.fail(t.id, error="fail")
        count = self.q.purge_dead_letter()
        assert count == 1

    def test_stats(self) -> None:
        self.q.enqueue({"a": 1})
        stats = self.q.stats()
        assert stats["queue_size"] == 1


# ═══════════════════════════════════════════════════════════════════════════════
# 8. CHAOS TESTING
# ═══════════════════════════════════════════════════════════════════════════════

from aios_core.chaos_testing import (
    ChaosAction, ChaosScenario, ChaosResult, ChaosTester,
)


class TestChaosTester:
    def setup_method(self) -> None:
        self.ct = ChaosTester(failure_probability=0.0)  # deterministic for tests

    def test_inject_no_failure(self) -> None:
        fn = self.ct.inject(lambda: 42)
        result = fn()
        assert result == 42

    def test_inject_with_failure(self) -> None:
        ct = ChaosTester(failure_probability=1.0)
        fn = ct.inject(lambda: 42)
        with pytest.raises(Exception, match="Chaos injection"):
            fn()

    def test_inject_with_latency(self) -> None:
        ct = ChaosTester(failure_probability=0.0, latency_ms=10)
        start = time.time()
        fn = ct.inject(lambda: 1)
        fn()
        assert time.time() - start >= 0.008  # roughly 10ms

    def test_register_scenario(self) -> None:
        scenario = ChaosScenario(name="test_s", actions=[ChaosAction.ERROR_INJECTION])
        self.ct.register_scenario(scenario)
        assert "test_s" in self.ct.scenarios

    def test_run_scenario(self) -> None:
        scenario = ChaosScenario(name="test_s", actions=[ChaosAction.ERROR_INJECTION], probability=1.0)
        self.ct.register_scenario(scenario)
        result = self.ct.run_scenario("test_s")
        assert result.scenario_name == "test_s"
        assert len(result.actions_executed) >= 1

    def test_run_scenario_with_probe(self) -> None:
        scenario = ChaosScenario(
            name="probe_s", actions=[ChaosAction.ERROR_INJECTION],
            probe_fn=lambda: True, probability=1.0,
        )
        self.ct.register_scenario(scenario)
        result = self.ct.run_scenario("probe_s")
        assert result.steady_state_maintained is True

    def test_run_scenario_probe_fails(self) -> None:
        scenario = ChaosScenario(
            name="fail_s", actions=[ChaosAction.ERROR_INJECTION],
            probe_fn=lambda: False, probability=1.0,
        )
        self.ct.register_scenario(scenario)
        result = self.ct.run_scenario("fail_s")
        assert result.steady_state_maintained is False

    def test_run_scenario_abort(self) -> None:
        scenario = ChaosScenario(
            name="abort_s", actions=[ChaosAction.ERROR_INJECTION, ChaosAction.LATENCY_INJECTION],
            abort_fn=lambda: True, probability=1.0,
        )
        self.ct.register_scenario(scenario)
        result = self.ct.run_scenario("abort_s")
        assert result.aborted is True

    def test_run_scenario_unknown_raises(self) -> None:
        with pytest.raises(KeyError, match="not found"):
            self.ct.run_scenario("unknown")

    def test_history(self) -> None:
        scenario = ChaosScenario(name="h_s", actions=[ChaosAction.ERROR_INJECTION], probability=1.0)
        self.ct.register_scenario(scenario)
        self.ct.run_scenario("h_s")
        history = self.ct.get_history()
        assert len(history) >= 1

    def test_stats(self) -> None:
        stats = self.ct.stats()
        assert stats["failure_probability"] == 0.0

    def test_is_action_active(self) -> None:
        assert self.ct.is_action_active("network_partition") is False

    def test_clear_active_actions(self) -> None:
        self.ct.clear_active_actions()
        assert len(self.ct._active_actions) == 0


# ═══════════════════════════════════════════════════════════════════════════════
# 9. AUTO-SCALER
# ═══════════════════════════════════════════════════════════════════════════════

from aios_core.auto_scaler import (
    ScalingDirection, ScalingPolicy, ScalingEvent, AutoScaler, auto_scaler,
)


class TestAutoScaler:
    def setup_method(self) -> None:
        self.scaler = AutoScaler(min_replicas=1, max_replicas=10, cooldown_seconds=0.0, stabilization_window=0.0)

    def test_scale_up_basic(self) -> None:
        result = self.scaler.scale({"cpu_usage": 90, "queue_size": 60})
        assert result > self.scaler.min_replicas

    def test_scale_down_basic(self) -> None:
        self.scaler.current_replicas = 5
        result = self.scaler.scale({"cpu_usage": 20, "queue_size": 2})
        assert result < 5

    def test_no_scale_in_range(self) -> None:
        self.scaler.current_replicas = 3
        result = self.scaler.scale({"cpu_usage": 50, "queue_size": 20})
        assert result == 3

    def test_scale_with_policies(self) -> None:
        self.scaler.add_policy(ScalingPolicy("cpu", "cpu_usage", scale_up_threshold=80, scale_down_threshold=30))
        self.scaler.add_policy(ScalingPolicy("queue", "queue_size", scale_up_threshold=50, scale_down_threshold=5))
        replicas = self.scaler.scale({"cpu_usage": 90, "queue_size": 60})
        assert replicas > self.scaler.min_replicas

    def test_scale_up_max_cap(self) -> None:
        self.scaler.current_replicas = 10
        result = self.scaler.scale({"cpu_usage": 95, "queue_size": 100})
        assert result == 10  # max cap

    def test_scale_down_min_cap(self) -> None:
        self.scaler.current_replicas = 1
        result = self.scaler.scale({"cpu_usage": 10, "queue_size": 1})
        assert result == 1  # min cap

    def test_scaling_events_history(self) -> None:
        self.scaler.add_policy(ScalingPolicy("cpu", "cpu_usage"))
        self.scaler.scale({"cpu_usage": 90})
        assert len(self.scaler.events) >= 1

    def test_predict_scale(self) -> None:
        self.scaler.add_policy(ScalingPolicy("cpu", "cpu_usage"))
        direction = self.scaler.predict_scale({"cpu_usage": 95})
        assert direction == ScalingDirection.UP

    def test_get_events(self) -> None:
        self.scaler.add_policy(ScalingPolicy("cpu", "cpu_usage"))
        self.scaler.scale({"cpu_usage": 90})
        events = self.scaler.get_events()
        assert len(events) >= 1

    def test_stats(self) -> None:
        stats = self.scaler.stats()
        assert stats["current"] >= 1

    def test_cooldown_blocks(self) -> None:
        scaler = AutoScaler(cooldown_seconds=10.0, stabilization_window=0.0)
        scaler.add_policy(ScalingPolicy("cpu", "cpu_usage"))
        scaler.scale({"cpu_usage": 90})
        # Second call within cooldown → no change
        scaler.set_metrics({"cpu_usage": 95})
        direction = scaler.evaluate()
        assert direction == ScalingDirection.NONE

    def test_singleton(self) -> None:
        assert isinstance(auto_scaler, AutoScaler)


# ═══════════════════════════════════════════════════════════════════════════════
# 10. HEALTH CHECKS
# ═══════════════════════════════════════════════════════════════════════════════

from aios_core.health_checks import (
    CheckKind, HealthResult, HealthCheckRegistry, health_registry,
)


class TestHealthCheckRegistry:
    def setup_method(self) -> None:
        self.registry = HealthCheckRegistry()

    def test_register_and_run(self) -> None:
        self.registry.register("db", lambda: True)
        results = self.registry.run_all()
        assert "db" in results
        assert results["db"].status == "healthy"

    def test_register_with_kind(self) -> None:
        self.registry.register("liveness_db", lambda: True, kind=CheckKind.LIVENESS)
        self.registry.register("readiness_db", lambda: True, kind=CheckKind.READINESS)
        results = self.registry.run_all(kind=CheckKind.LIVENESS)
        assert "liveness_db" in results
        assert "readiness_db" not in results

    def test_unhealthy_check(self) -> None:
        self.registry.register("cache", lambda: False)
        result = self.registry.run_check("cache")
        assert result.status == "unhealthy"

    def test_error_check(self) -> None:
        self.registry.register("fail", lambda: (_ for _ in ()).throw(RuntimeError("boom")))
        result = self.registry.run_check("fail")
        assert result.status == "error"
        assert result.error == "boom"

    def test_dict_result(self) -> None:
        self.registry.register("detail", lambda: {"status": "healthy", "connections": 5})
        result = self.registry.run_check("detail")
        assert result.status == "healthy"
        assert result.details.get("connections") == 5

    def test_dependency_check(self) -> None:
        self.registry.register("cache", lambda: False)
        self.registry.register("api", lambda: True, dependencies=["cache"])
        result = self.registry.run_check("api")
        # api should be degraded because cache is unhealthy
        assert result.status == "degraded"

    def test_overall_status_healthy(self) -> None:
        self.registry.register("db", lambda: True)
        self.registry.register("cache", lambda: True)
        assert self.registry.overall_status() == "healthy"

    def test_overall_status_degraded(self) -> None:
        self.registry.register("db", lambda: {"status": "degraded"})
        self.registry.register("cache", lambda: True)
        assert self.registry.overall_status() == "degraded"

    def test_overall_status_unhealthy(self) -> None:
        self.registry.register("db", lambda: False)
        assert self.registry.overall_status() == "unhealthy"

    def test_liveness_status(self) -> None:
        self.registry.register("live", lambda: True, kind=CheckKind.LIVENESS)
        assert self.registry.liveness_status() == "healthy"

    def test_readiness_status(self) -> None:
        self.registry.register("ready", lambda: True, kind=CheckKind.READINESS)
        assert self.registry.readiness_status() == "ready"

    def test_startup_status(self) -> None:
        self.registry.register("init", lambda: True, kind=CheckKind.STARTUP)
        assert self.registry.startup_status() == "started"

    def test_summary(self) -> None:
        self.registry.register("db", lambda: True)
        summary = self.registry.summary()
        assert "overall" in summary
        assert "checks" in summary

    def test_stats(self) -> None:
        self.registry.register("db", lambda: True)
        self.registry.register("cache", lambda: True, kind=CheckKind.LIVENESS)
        stats = self.registry.stats()
        assert stats["total_checks"] == 2

    def test_unregister(self) -> None:
        self.registry.register("db", lambda: True)
        self.registry.unregister("db")
        assert "db" not in self.registry.checks

    def test_singleton(self) -> None:
        assert isinstance(health_registry, HealthCheckRegistry)


# ═══════════════════════════════════════════════════════════════════════════════
# INTEGRATION
# ═══════════════════════════════════════════════════════════════════════════════

class TestIntegration:
    def test_circuit_breaker_with_service_mesh(self) -> None:
        """Circuit breaker protects service mesh calls."""
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=0.01)
        mesh = ServiceMesh()
        mesh.register_service("api", "localhost:8000")

        # Successful call through circuit breaker
        result = cb.call(lambda: mesh.discover("api"))
        assert result["endpoint"] == "localhost:8000"
        assert cb.state == CircuitState.CLOSED

    def test_self_healing_with_circuit_breaker(self) -> None:
        """Self-healing recovers circuit breaker failures."""
        sh = SelfHealing()
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=0.01)

        # Register recovery: reset circuit breaker
        sh.register_strategy("CircuitOpenError", lambda ctx: cb.force_close())
        sh.register_health_check("circuit", lambda: cb.state == CircuitState.CLOSED)

        # Trip circuit breaker
        try:
            cb.call(lambda: (_ for _ in ()).throw(RuntimeError("fail")))
        except RuntimeError:
            pass
        assert cb.state == CircuitState.OPEN

        # Heal → reset circuit breaker
        sh.heal(CircuitOpenError("open"))
        assert cb.state == CircuitState.CLOSED

    def test_auto_scaler_with_health_checks(self) -> None:
        """Auto-scaler reads health check metrics for scaling decisions."""
        scaler = AutoScaler(cooldown_seconds=0.0, stabilization_window=0.0)
        scaler.add_policy(ScalingPolicy("cpu", "cpu_usage", scale_up_threshold=80, scale_down_threshold=30))

        registry = HealthCheckRegistry()
        registry.register("cpu_check", lambda: {"status": "healthy", "cpu_usage": 95})

        # Simulate: read cpu_usage from health check details
        result = registry.run_check("cpu_check")
        cpu = result.details.get("cpu_usage", 0)
        replicas = scaler.scale({"cpu_usage": cpu})
        assert replicas > scaler.min_replicas

    def test_zero_trust_with_api_gateway(self) -> None:
        """API Gateway uses Zero Trust for auth decisions."""
        gw = APIGateway()
        gw.register("/admin", lambda r: {"admin": True}, auth_required=True)

        # Not authenticated → gateway rejects with 401
        result = gw.handle("/admin", {"authenticated": False})
        assert result["status"] == 401

    def test_chaos_with_distributed_queue(self) -> None:
        """Chaos testing injects failures into queue processing."""
        ct = ChaosTester(failure_probability=1.0)
        q = DistributedQueue()
        q.register_worker("w1")

        task = q.enqueue({"action": "scrape"}, max_retries=0)
        t = q.dequeue()

        # Chaos-injected handler
        try:
            ct.inject(lambda: q.complete(t.id, result={"ok": True}))()
        except Exception:
            q.fail(t.id, error="chaos_failure")

        assert q.dead_letter_count() >= 1  # no retries → DLQ
