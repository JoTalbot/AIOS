# AIOS v11.37.0 — Release Notes

**Release Date**: 2026-07-30

---

## Highlights

### 1. Autonomous Vision RPA & Browser Action Grounding (`VisionRPAGroundingEngine`)
- Added `VisionRPAGroundingEngine` in `aios_core/vision_rpa_grounding.py`.
- Grounds natural language RPA action descriptions to exact UI element IDs and screen click coordinates (x, y).
- REST API: `POST /api/ai/perception/ground-action`.
- SDK: `ai_ground_rpa_action()`.

---

## Test Suite Status
- **4383 passed, 0 failed**
