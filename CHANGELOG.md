# AIOS Changelog

All notable changes to this project will be documented in this file.

## [4.1.0-alpha] - 2026-07-21

### Added
- **Constitutional Verification Tool (`tula`)** — autonomous tool (`tools/complete_constitution_tula.py`) for scanning articles I-LXVII, strict structure verification, compliance matrix generation, master index tracking, and report generation.
- **AI Safety & Ethics Test Suite** — comprehensive unit tests for safety layers, real-time safety monitor, dashboard, ethics evaluator, and benchmarks (`tests/test_ai_safety_framework.py`).
- **Cognition & Role Engine Test Suite** — unit tests for Theory of Mind, Emotional Intelligence, Metacognition, Social Intelligence, Creativity, AI Scientist, AI Researcher, AI Engineer, AI Product Manager, AI Startup (`tests/test_cognition_framework.py`).
- **Constitutional Verification Test Suite** — automated test suite for `tula` (`tests/test_tula.py`).
- Total test coverage expanded to **526 passed tests** (100% passing).

### Changed
- Unified versioning across `aios_core/__init__.py`, REST API `/health`, and tests to `4.1.0-alpha`.
- Fixed typing and compilation constraints in `ai_safety_evals.py` and `ai_safety_benchmark.py`.
- Updated `docs/constitution/COMPLIANCE_MATRIX.md`, `docs/constitution/INDEX.md`, and `docs/constitution/CONSTITUTION_REPORT.md` with full 67-article mapping.

## [4.0.0-alpha] - 2026-07-21

### Added
- **FederationManager** — multi-node coordination, task delegation, broadcast
- **MLPlannerScorer** — ML-enhanced plan scoring and optimization
- **MultiAgentOrchestrator** — dynamic team formation and conflict resolution
- **ConstitutionEvolver** — self-evolving constitution with automatic proposals
- **Web Dashboard** — real-time monitoring interface (Starlette)
- Full integration of all v4.0 subsystems into `Orchestrator`
- 20+ new tests for v4.0 components (total: 501 passing)

### Changed
- `Orchestrator.stats()` now includes `federation`, `ml_scorer`, `multi_agent`, `constitution_evolver`
- Enhanced autonomy with automatic level adjustment
- Improved monitoring (`/metrics`, `monitor.py`)

### Infrastructure
- Docker + docker-compose support
- Prometheus-compatible metrics
- Production-ready deployment files

## [3.1.0] - 2026-07-21

### Added
- Enhanced monitoring and health endpoints
- Docker support
- 485+ tests

## [3.0.0] - 2026-07-19

Initial stable release with full constitution (67 articles), orchestrator, evolution, and API layers.

---

**Next milestone:** v4.1 (Kubernetes operator, official SDK, capability marketplace)