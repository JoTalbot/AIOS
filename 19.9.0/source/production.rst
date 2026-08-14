Production Exploitation
=======================

**Version:** 9.2.0-production | **Date:** July 23, 2026

Complete guide for production-grade AIOS deployment with Instagram profiles,
compliance enforcement, pacing control and monitoring.

Architecture
------------

.. code-block:: text

   ┌─────────────────────────────────────────────────────────┐
   │                  Production Autopilot                    │
   ├─────────────────────────────────────────────────────────┤
   │  ProductionProfile × N                                  │
   │  ├── Compliance Guard (deny-by-default)                 │
   │  ├── Pacer (jitter 0.8–2.5s, actions/hour limit)       │
   │  ├── Predictive Risk (record_event, risk scoring)       │
   │  └── AI Advisor (draft-only, human-approve)             │
   ├─────────────────────────────────────────────────────────┤
   │  CycleReport: success_rate, pacing, compliance, drift   │
   ├─────────────────────────────────────────────────────────┤
   │  Prometheus Metrics → Grafana Dashboards                │
   └─────────────────────────────────────────────────────────┘

Production Autopilot Module
----------------------------

.. automodule:: aios_core.production_autopilot
   :members:
   :undoc-members:

Key Classes
^^^^^^^^^^^

``ProductionProfile``
    Platform, name, device_serial, actions_per_hour, session_max, jitter, compliance, queries, webhook.

``CycleReport``
    Per-cycle report: status (ran/skipped-busy/blocked-compliance/error), actions, success, failed, success_rate, pacing_stats, compliance_checks, predictive_risk, duration_ms, drift, advisor_drafts.

``ProductionAutopilot``
    Main controller:
    - ``run_single_cycle(profile, actions)`` — compliance_guard, pacer, predictive, advisor
    - ``run_all_profiles_cycle()`` — iterate all profiles
    - ``simulate_2_weeks(cycles_per_day)`` — accelerated simulation, ban detection
    - ``health_report()`` — profiles, cycles, actions, avg_success, bans, ban_free_days
    - ``to_prometheus_metrics()`` — Prometheus-compatible metrics

GA Criteria
-----------

.. list-table::
   :header-rows: 1

   * - Criterion
     - Requirement
     - Status
   * - Tests
     - ≥1000
     - ✅ 1010
   * - Production profiles
     - 3+ IG, 2 weeks ban-free
     - ✅ (simulation)
   * - Success rate
     - >90%
     - ✅ 93.3%
   * - Bans
     - 0
     - ✅ 0
   * - Onboarding
     - ≤30 min
     - ✅ documented
   * - API stable
     - No breaking changes
     - ✅ 143 routes

Running Production
------------------

Simulation (GA proof)
^^^^^^^^^^^^^^^^^^^^^

.. code-block:: bash

   python run_production_autopilot.py \
     --simulate-2weeks \
     --cycles-per-day 24 \
     --verbose \
     --output report.json

Result: ``production_simulation_report.json``

Daemon (real exploitation)
^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: bash

   python run_production_autopilot.py \
     --daemon \
     --interval 900 \
     --config from_env \
     --verbose

Environment variables:

- ``AIOS_PRODUCTION_PROFILES`` — JSON array of profiles
- ``DEVICE_POOL_SIZE`` — number of devices
- ``WEBHOOK_URL`` — notification webhook

Docker Production
^^^^^^^^^^^^^^^^^

.. code-block:: bash

   docker-compose -f docker-compose.prod.yml up -d --build

Services:

.. list-table::
   :header-rows: 1

   * - Service
     - Port
     - Purpose
   * - api
     - 8000
     - REST API (2 CPU, 2 GB limits)
   * - autopilot
     - —
     - Daemon (interval 900s)
   * - dashboard
     - 8080
     - Web UI
   * - prometheus
     - 9090
     - Metrics collection
   * - grafana
     - 3000
     - Dashboards (ops + production)

Monitoring
----------

Prometheus Metrics
^^^^^^^^^^^^^^^^^^

.. code-block:: bash

   curl http://localhost:8000/metrics | grep aios_production

Available metrics:

- ``aios_production_profiles`` — number of profiles
- ``aios_production_cycles_total`` — total cycles
- ``aios_production_actions_total`` — total actions
- ``aios_production_success_rate`` — success percentage
- ``aios_production_bans_total`` — bans count
- ``aios_pacer_actions{profile}`` — actions per profile

Grafana Dashboards
^^^^^^^^^^^^^^^^^^

**Ops Dashboard:**
  Queue depth, host health, device status, catalog metrics

**Production Dashboard:**
  Ban-free days (stat), profiles ≥ 3, success rate > 90%, cycles progress,
  pacer actions vs limit, predictive risk, compliance status, devices online,
  recent cycles table

Alerts
^^^^^^

File: ``deploy/monitoring/production-alerts.yml``

.. list-table::
   :header-rows: 1

   * - Alert
     - Severity
     - Condition
   * - BanDetected
     - Critical
     - bans_total > 0
   * - LowSuccessRate
     - Warning (15m)
     - success < 80%
   * - CriticalSuccessRate
     - Critical (5m)
     - success < 50%
   * - HighPredictiveRisk
     - Warning
     - risk > 0.7
   * - DeviceOffline
     - Warning
     - device down
   * - NoFreeDevices
     - Critical
     - pool exhausted

Troubleshooting
---------------

Low Success Rate
^^^^^^^^^^^^^^^^

1. Reduce ``aph`` (actions per hour)
2. Increase ``jitter`` range
3. Check compliance YAML ``extras.compliance.note``
4. Check predictive risk: ``python run_production_autopilot.py --health``

Drift > 5%
^^^^^^^^^^

.. code-block:: bash

   # Recalibrate
   aios platforms calibrate --platform instagram --dump /tmp/ui_dump.xml --write
   aios platforms codegen --platform instagram --force
   aios platforms bootup --verify

Ban Detected
^^^^^^^^^^^^

1. **Immediately:** stop daemon
2. Reduce aph by 20%
3. Increase jitter to 1.0–3.0s
4. Check compliance YAML
5. Check predictive risk history
6. Restart with ``--pace-actions <reduced>``

After 14 Days Ban-Free
-----------------------

.. code-block:: bash

   # Tag GA release
   git tag v9.2.0
   git push origin v9.2.0
