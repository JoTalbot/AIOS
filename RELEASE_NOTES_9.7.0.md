# AIOS v9.7.0 Release Notes

**Release Date**: 2026-07-24  
**Tag**: `v9.7.0`  
**Tests**: 1327 passing, 0 failures ✅

---

## New Modules

### cross_platform_comparator.py — Multi-Platform Price Comparison
- `CrossPlatformComparator` — compares products across OLX, Rozetka, Prom, Shafa
- `ComparisonGroup` — grouped products with lowest_price, highest_price, average_price, spread_pct, best_platform
- `compare(query)` — find and compare products across all registered platforms
- `compare_product(fingerprint, platform)` — find same product on other platforms
- `arbitrage_opportunities(min_spread_pct)` — detect arbitrage opportunities
- Title similarity via token overlap (Jaccard-like, no external dependencies)

### ai_advisor_v2.py — Cross-Platform Recommendation Engine
- `AICrossPlatformAdvisor` — extends AISalesAdvisor with cross-platform analysis
- `recommend_cross_platform(title)` — buy/sell recommendations with arbitrage detection
- `predict_price(storage, fingerprint, horizon_days)` — simple linear regression price prediction
- `full_analysis(title, storage, fingerprint)` — combined comparison + prediction + advice

### vector_search.py — Lightweight TF-IDF Product Matching
- `VectorSearchEngine` — pure Python TF-IDF vector search (no external embedding model)
- `build_index()` — builds vocabulary and TF-IDF vectors from storage
- `search(query, limit)` — find products matching a text query
- `find_similar(fingerprint, limit)` — find products similar to a reference
- Configurable: min_term_freq, max_vocab_size, cosine similarity threshold

### ws_dashboard.py — WebSocket Real-Time Event Streaming
- `DashboardEventBus` — in-memory event bus for streaming dashboard events
- `WSMessage` — typed messages (PRICE_DROP, AUTOWATCH_CYCLE, CROSS_PLATFORM, SYSTEM_STATUS, FAVORITE_ALERT, VECTOR_MATCH)
- `create_ws_dashboard_app()` — Starlette app with `/ws/dashboard` WebSocket route
- Replay buffer for late-joining clients (50 recent events)
- `emit_price_drop`, `emit_autowatch`, `emit_cross_platform` — convenient message creators

### benchmarks_thresholds.py — CI Regression Gate
- 10 performance thresholds for key operations
- `check_threshold(name, actual_ms)` — pass/fail with percentage breakdown
- Blocking CI job — fails if any benchmark exceeds its threshold
- Thresholds: core_import 500ms, storage_save_ads_100 50ms, rate_limiter 1ms, vector_search 50ms, etc.

---

## New CLI Subcommands

### Cross-Platform
```bash
aios cross-platform compare --olx-db olx.sqlite --rozetka-db rozetka.sqlite --query "iPhone"
aios cross-platform product --fingerprint fp123 --platform olx --olx-db olx.sqlite
aios cross-platform arbitrage --min-spread 10 --olx-db olx.sqlite --rozetka-db rozetka.sqlite
```

### AI Advisor v2
```bash
aios advisor-v2 recommend --title "iPhone 16" --olx-db olx.sqlite --rozetka-db rozetka.sqlite
aios advisor-v2 predict --fingerprint fp123 --platform olx --db olx.sqlite --horizon 14
aios advisor-v2 analyze --title "Phone" --fingerprint fp123 --olx-db olx.sqlite
```

### Vector Search
```bash
aios search query --text "iPhone" --platform olx --db olx.sqlite --limit 10
aios search similar --fingerprint fp123 --platform rozetka --db rozetka.sqlite
```

### Benchmarks
```bash
aios benchmarks list
aios benchmarks check --name core_import --actual-ms 450
```

---

## New Tests (47 total)

- 10 test_cross_platform_comparator (groups, prices, similarity, compare, product, arbitrage, no_match, enum)
- 8 test_vector_search (build, empty, query, similar, dict, no_storage, min_freq, cosine)
- 9 test_ws_dashboard (types, json, init, emit_price_drop, autowatch, cross_platform, buffer, app, default)
- 10 test_benchmarks_thresholds (list, dict, get, missing, pass, fail, unknown, edge, all, reasonable)
- 7 test_ai_advisor_v2 (dataclass, init, prediction, insufficient, stable, full_analysis)
- 4 test_cli_v970 (cross_platform, advisor_v2, search, benchmarks subparsers)

---

## CI Changes
- Benchmarks job now **blocking** — fails CI if any threshold exceeded
- Thresholds validated in CI before pytest-benchmark runs

---

## Breaking Changes
None — all changes are backward-compatible.

## Migration Guide
No migration required. Update `pip install aios==9.7.0`.

---

## Contributors
- JoTalbot (jo.talbot@gmail.com)

## Next: v9.8.0
- TikTok full agent, WhatsApp/Viber/FB full agents
- Multi-account fleet scheduler
- Production dashboard React v3
- See [ROADMAP_NEXT.md](ROADMAP_NEXT.md) for full roadmap
