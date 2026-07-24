# AIOS v10.5.0 Release Notes

**Date**: 2026-07-24  
**Version**: 10.5.0  
**Tests**: 2032 passed, 0 failures (+150 new, +2 fixed)  

## New Modules — 10 Stub → Full Implementations

### 1. Zero Trust Security (`zero_trust.py`) — 26→230 lines
- Trust levels (UNTRUSTED → FULLY_TRUSTED) with score 0–100
- Device profiles with trust scoring (fingerprint, platform, MFA, verified_device)
- Trust policies with conditions (list, nested dict, attribute matching)
- Network segmentation (CIDR IP range checks)
- Continuous verification engine with audit trail
- Backward-compatible ZeroTrust façade

### 2. Self-Healing System (`self_healing.py`) — 55→190 lines
- Recovery escalation (LIGHT → MODERATE → SEVERE → CRITICAL)
- Health monitor with TTL caching (stale → re-run)
- Recovery history tracking with success/failure records
- Max recovery attempts with auto-reset on success
- Diagnostic analysis (health + recovery history + recurring errors)
- Configurable escalation threshold

### 3. Circuit Breaker (`circuit_breaker.py`) — 52→200 lines
- Half-open probing with configurable probe calls
- Fallback function support for OPEN state
- Detailed metrics (success, failure, trip, rejection counts, success rate)
- State change listeners (old → new notification)
- CircuitOpenError exception class
- Manual force_open / force_close / reset
- Stabilization: requires N successful probes before closing

### 4. API Gateway (`api_gateway.py`) — 34→220 lines
- Route registration with HTTP methods, versions, rate limits, auth
- Middleware pipeline (pre-processing chain)
- Per-route sliding-window rate limiting (requests per 60s)
- Authentication middleware check (401 response)
- Method checking (405 response for wrong methods)
- Route versioning (v1, v2, etc.)
- Health endpoint and request metrics tracking

### 5. Graceful Shutdown (`graceful_shutdown.py`) — 46→170 lines
- Phase-based shutdown: DRAIN → CLEANUP → FINALIZE
- Priority ordering within each phase (lower = runs first)
- Per-hook timeout and per-phase timeout
- Progress tracking with detailed report
- Named hooks with phase assignment
- Backward-compatible register_handler() API

### 6. Service Mesh (`service_mesh.py`) — 35→250 lines
- Service registration with health status and metadata
- Service discovery with status filtering
- Traffic splitting (canary, blue-green) with weighted random selection
- Health checking integration with auto-status updates
- Load balancing (round_robin, random, weighted strategies)
- Unhealthy/degraded status tracking

### 7. Distributed Queue (`distributed_queue.py`) — 41→230 lines
- Priority-based ordering (CRITICAL → HIGH → NORMAL → LOW)
- Worker registration with capacity tracking
- Retry policy per task (max_retries, retry_count)
- Dead letter queue for permanently failed tasks
- DLQ retry and purge operations
- Task lifecycle: QUEUED → RUNNING → COMPLETED/FAILED/DEAD
- Backward-compatible enqueue/dequeue/size API

### 8. Chaos Testing (`chaos_testing.py`) — 34→200 lines
- Scenario-based chaos (not just random injection)
- 6 action types: network partition, latency, error, CPU stress, memory stress, service kill
- Steady-state validation (probe before and after injection)
- Abort conditions (stop if system unrecoverable)
- Execution history with per-scenario results
- Per-action probability and latency configuration
- Backward-compatible inject() decorator

### 9. Auto-Scaler (`auto_scaler.py`) — 32→230 lines
- Multiple metric threshold policies (cpu, queue, error_rate, latency)
- Cooldown period between scaling decisions
- Stabilization window (delay before scaling down after up)
- Scaling events history with reasons and metrics
- Predictive scaling based on projected metrics
- HPA-like behavior (scale_up_step, scale_down_step)
- Backward-compatible scale(cpu_usage, queue_size) API

### 10. Health Checks (`health_checks.py`) — 42→180 lines
- Liveness/Readiness/Startup distinction (Kubernetes model)
- TTL caching (don't re-run within TTL window)
- Dependency checks (service A depends on service B)
- Aggregate health status computation (healthy/degraded/unhealthy)
- Dict-based check results (status + details)
- Error handling (status="error" with error message)
- Full health summary (overall, liveness, readiness, startup)

## Bug Fixes
- Circuit breaker scenario tests: updated for new half_open_max_calls API
- Circuit breaker: requires N successful probes before transitioning HALF_OPEN → CLOSED

## Integration Tests (5 cross-module)
- Circuit Breaker + Service Mesh: breaker protects mesh service calls
- Self-Healing + Circuit Breaker: healing recovers breaker from OPEN state
- Auto-Scaler + Health Checks: scaler reads health metrics for decisions
- Zero Trust + API Gateway: gateway uses auth for access control
- Chaos + Distributed Queue: chaos injects failures into queue processing

## Test Coverage: 150 new tests
- Zero Trust: 15 tests (DeviceProfile, TrustPolicy, TrustEngine, Façade)
- Self-Healing: 9 tests (HealthMonitor, SelfHealing with escalation)
- Circuit Breaker: 12 tests (Metrics, state transitions, fallback, listeners)
- API Gateway: 13 tests (routes, middleware, rate limit, auth, versioning)
- Graceful Shutdown: 8 tests (phases, order, failure, progress)
- Service Mesh: 11 tests (discovery, traffic, health checks, load balance)
- Distributed Queue: 10 tests (priority, workers, retry, DLQ)
- Chaos Testing: 13 tests (inject, scenarios, probes, abort)
- Auto-Scaler: 11 tests (policies, events, cooldown, prediction)
- Health Checks: 13 tests (kinds, dependencies, aggregate, summary)

## Previous Versions
- v10.4.0: Feature Flags + RBAC + Workflow Engine (212 tests)
- v10.3.0: Agent Memory + Platform Health + Export/Import (54 tests)
- v10.2.0: Credential Manager + Price Alert + Scraping Templates (58 tests)
