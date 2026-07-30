# AIOS v11.23.0 — Release Notes

**Release Date**: 2026-07-30

---

## Highlights

### 1. Real-Time Pre-Execution Safety Guard (`AgentSafetyComplianceGuard`)
- Added `AgentSafetyComplianceGuard` in `aios_core/ai_governance.py`.
- Evaluates agent actions pre-execution for harm risk, deception risk, and policy violations.
- Automatically blocks high/critical risk actions and records accountability audit logs.

### 2. Autonomous Safety Audit Engine (`AutonomousSafetyAuditEngine`)
- Added `AutonomousSafetyAuditEngine` in `aios_core/ai_governance.py`.
- Calculates composite Governance Compliance Index (0..100) combining policy audit scores, memory vitality scores, and energy budget statuses.

### 3. REST API & Developer SDK Integration
- Endpoints:
  - `POST /api/governance/guard/evaluate`
  - `POST /api/governance/audit/run`
  - `GET /api/governance/compliance/score`
- Added SDK methods `evaluate_action_safety()`, `run_safety_audit()`, and `get_compliance_score()` to `AIOSClient` and `AIOSClientSync`.

---

## Test Suite Status
- **4368 passed, 0 failed**
