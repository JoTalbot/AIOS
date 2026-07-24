# RELEASE_NOTES — AIOS v10.3.0

**Release Date:** 2026-07-24
**Test Suite:** 1670 tests passing, 0 failures

## 🚀 Major New Features

### 1. Agent Memory System (`aios_core/agent_memory_system.py`)
Long-term memory for scraping agents with learning and adaptation:

- **Memory Types** — SHORT_TERM, LONG_TERM, EPISODIC, PROCEDURAL
- **Memory Strength Decay** — exponential decay with frequency-based reinforcement
- **Consolidation** — summarize episodic into long-term insights (success rates, patterns)
- **Success Pattern Extraction** — identify best params/configurations per platform
- **Advice Engine** — `get_advice()` returns recommended params + warnings + avoid lists
- **Block Detection** — critical priority for ban/block events
- **Session Recording** — `record_session()` with latency, items, errors, params
- **Memory Priority** — CRITICAL, HIGH, NORMAL, LOW, TRIVIAL

### 2. Platform Health Monitor (`aios_core/platform_health_monitor.py`)
Real-time platform health monitoring for fleet optimization:

- **Health Scores** — composite 0-100 score (success rate, latency, block risk, consecutive)
- **Health Status** — HEALTHY, DEGRADED, UNSTABLE, BLOCKED, DOWN, UNKNOWN
- **Block Detection** — automatic detection when platform blocks scraping agents
- **Success/Failure Reporting** — simple API for fleet devices to report status
- **Degradation Detection** — find platforms below health threshold
- **Platform Comparison** — compare health across all monitored platforms
- **Best Platform Selection** — find healthiest platform for scraping
- **Consecutive Failure Tracking** — mark DOWN after N consecutive failures

### 3. Export/Import Pipeline (`aios_core/export_import_pipeline.py`)
Data export/import with format conversion and schema validation:

- **JSON Export/Import** — with schema version and validation
- **CSV Export/Import** — with field mapping and type inference
- **Gzip JSON Export** — compressed export for large datasets
- **Schema Validation** — required fields, type checking
- **Import Modes** — REPLACE, APPEND, UPSERT, MERGE
- **Incremental Export** — only changed records since last export
- **Field Mapping** — rename fields between formats
- **Default Schema** — product/ad data schema (fingerprint, title, price, etc.)

## 🔧 Bug Fixes

- `AgentMemorySystem.recall()` — removed unsupported `priority` keyword arg in `get_advice()`

## 🧪 Tests

- `test_v10_3_modules.py` — 54 tests (memory, health, export/import)
- **1670 total tests, 0 failures**

## 📊 Version Bump

- v10.2.0 → **v10.3.0**

## 📁 New Files

- `aios_core/agent_memory_system.py`
- `aios_core/platform_health_monitor.py`
- `aios_core/export_import_pipeline.py`
- `tests/test_v10_3_modules.py`
