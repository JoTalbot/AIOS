# AIOS v11.27.0 — Release Notes

**Release Date**: 2026-07-30

---

## Highlights

### 1. Multimodal Agent Perception Engine (`MultimodalPerceptionEngine`)
- Added `MultimodalPerceptionEngine` in `aios_core/multimodal_perception.py`.
- Extracts actionable UI element bounding boxes, text OCR, and suggested RPA actions from UI screenshots.
- REST API: `POST /api/ai/perception/ui`.
- SDK: `ai_process_visual_ui()`.

---

## Test Suite Status
- **4376 passed, 0 failed**
