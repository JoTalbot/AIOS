# AIOS Changelog

All notable changes to this project will be documented in this file.

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