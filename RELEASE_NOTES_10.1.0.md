# RELEASE_NOTES — AIOS v10.1.0

**Release Date:** 2026-07-24
**Test Suite:** 1558 tests passing, 0 failures

## 🚀 Major New Features

### 1. A/B Testing Engine (`aios_core/ab_testing_engine.py`)
Full-featured A/B testing for scraping strategy comparison:

- **Experiment Lifecycle** — draft → running → paused → completed → analyzed
- **Variant Tracking** — observations, success rates, confidence weights
- **Statistical Tests** — Chi-square for rate metrics, Welch's t-test for mean metrics
- **Significance Analysis** — p-value computation, confidence intervals, lift calculation
- **Auto-Completion** — automatically stop experiment when statistical significance reached
- **Normal CDF Approximation** — Abramowitz & Stegun polynomial approximation
- **Experiment Registry** — list, filter, cancel, pause experiments

### 2. Knowledge Graph (`aios_core/knowledge_graph.py`)
In-memory knowledge graph for product/seller relationships:

- **Triple Storage** — subject → predicate → object with weights and metadata
- **API-Compatible Methods** — add_node, add_relation, get_node, find_nodes, neighbors, path
- **Neighborhood Queries** — find related entities, multi-hop neighbors
- **Path Finding** — BFS shortest path with weight and confidence tracking
- **Inference Rules** — chain inference (sold_by+located_in → located_in, etc.)
- **Entity Types** — products, sellers, platforms, cities, categories
- **Upsert Support** — adding same node updates label/properties
- **DB Compatibility** — accepts db parameter (stored for future persistence)

### 3. Auto-Tuning Engine (`aios_core/auto_tuning.py`)
Dynamic scraping parameter optimization:

- **Parameter Registry** — INT, FLOAT, BOOL, CHOICE types with ranges
- **Grid Search** — exhaustive parameter space exploration
- **Random Search** — random sampling of configurations
- **Hill Climbing** — local perturbation around current best
- **Adaptive (Bayesian-style)** — 70% explore, 30% random, decreasing perturbation
- **Performance Feedback** — success rate, latency, items, errors → composite score
- **Automatic Best Tracking** — update best params when better configuration found
- **Scoring Functions** — default weighted (success*0.5 + latency*0.2 + items*0.3) or custom

## 🔧 Bug Fixes

- **KnowledgeGraph API Compatibility** — added `add_node()`, `add_relation()`, `get_node()`, `find_nodes()`, `neighbors()`, `path()`, `related()`, `count_nodes()` for backwards compatibility with existing Phase 1 and Phase 5 API tests
- **KnowledgeGraph.db parameter** — `__init__()` now accepts optional `db` parameter (stored but not used yet, for compatibility)
- **Orchestrator.knowledge** — changed `KnowledgeGraph(db=self.db)` to `KnowledgeGraph()` to match new API
- **KnowledgeGraph.stats()** — added `nodes` and `edges` aliases for API compatibility
- **add_relation()** — returns dict with both `subject/object` and `source/target` keys
- **16 async test methods** — added `@pytest.mark.asyncio` to all async methods in `test_admin_api.py`

## 🧪 Tests

- `test_v10_modules.py` — 44 tests (AB testing, Knowledge Graph, Auto-Tuning)
- All existing Phase 1 and Phase 5 Knowledge Graph tests now passing
- **1558 total tests, 0 failures**

## 📊 Version Bump

- v10.0.0 → **v10.1.0**

## 📁 New Files

- `aios_core/ab_testing_engine.py`
- `aios_core/knowledge_graph.py`
- `aios_core/auto_tuning.py`
- `tests/test_v10_modules.py`

## 📁 Modified Files

- `aios_core/orchestrator.py` — `KnowledgeGraph()` init fix
- `tests/test_admin_api.py` — 16 async methods fixed with @pytest.mark.asyncio
