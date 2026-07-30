# AIOS v11.19.0 — Release Notes

**Release Date**: 2026-07-30

---

## Highlights

### 1. REST API Auto-Throttle Endpoint (`/api/substrate/budget/throttle`)
- GET and POST endpoints for viewing and configuring energy budget auto-throttle settings.

### 2. REST API Policy Auto-Tune Endpoint (`/api/substrate/policy/autotune`)
- POST endpoint for triggering policy auto-tuning based on workload samples.

### 3. REST API Telemetry & Maintenance Endpoints
- `GET /api/memory/health`: memory vitality score, fragmentation ratio, archive pressure.
- `POST /api/memory/snapshot/prune`: backup snapshot TTL cleanup.
- `POST /api/retention/maintenance/run`: unified retention maintenance cycle (`confirm: true`).

---

## Test Suite Status
- **4355 passed, 0 failed**
