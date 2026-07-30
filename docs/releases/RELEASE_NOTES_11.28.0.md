# AIOS v11.28.0 — Release Notes

**Release Date**: 2026-07-30

---

## Highlights

### 1. Swarm Federated Learning & Consensus Engine (`SwarmFederatedEngine`)
- Added `SwarmFederatedEngine` in `aios_core/swarm_federated.py`.
- Aggregates privacy-preserving weight deltas, insights, and KnowledgeGraph statistics across distributed AIOS swarm nodes.
- REST API: `POST /api/ai/swarm/federated/aggregate`.
- SDK: `ai_aggregate_swarm_insights()`.

---

## Test Suite Status
- **4378 passed, 0 failed**
