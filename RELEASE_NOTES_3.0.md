# AIOS v3.0 Release Notes

**Release Date:** 2026-07-21  
**Version:** 3.1.0 (v3.0 feature complete)

## 🎉 Major Features

### 1. Enhanced Monitoring & Observability
- New `/metrics` endpoint (Prometheus compatible)
- Enhanced `/health` with live system stats
- `monitor.py` — standalone monitoring script
- Docker + docker-compose support

### 2. AutonomyManager v3.0
- **Automatic level adjustment** — agents are automatically promoted/demoted based on performance
- 5 autonomy levels (0–5)
- Risk-based approval matrix
- `should_promote()` / `should_demote()` heuristics

### 3. CapabilityEngine v3.0
- `suggest_capabilities()` — intelligent capability recommendations
- Based on usage patterns and failure rates
- Dynamic lifecycle management

### 4. Planner v3.0
- `score_plan()` — quality scoring for plans (0.0–1.0)
- `generate_multi_agent_plan()` — automatic multi-agent coordination plans
- Advanced DAG analysis

### 5. Production Readiness
- Full Docker support
- Health & metrics endpoints
- Comprehensive test coverage (485 tests)

## 📦 New Files

- `Dockerfile`
- `docker-compose.yml`
- `monitor.py`
- `VERSION_3.0.md`
- `RELEASE_NOTES_3.0.md`
- `tests/test_monitoring.py`
- `tests/test_evolution_autonomy_integration.py`
- `tests/test_autonomy_v3.py`
- `tests/test_capability_suggestions.py`
- `tests/test_planner_v3.py`

## 🔧 Improvements

- `orchestrator.stats()` now returns `constitution_articles`, `memory_items`, `evolution_proposals`, `active_tasks`
- Automatic autonomy adjustment after every `record_action()`
- Better Prometheus metrics format

## ✅ Test Results

**485 tests passed**

## 🚀 How to Upgrade

```bash
git pull
docker-compose up -d --build
```

Or run locally:

```bash
pip install -r requirements.txt
python -m pytest -q
python run_rest_api.py
```

## Next Steps (v3.1+)

- Machine Learning integration for Planner
- More advanced multi-agent orchestration
- Federation support

---

**AIOS v3.0 is now production-ready with strong autonomy and monitoring capabilities.**