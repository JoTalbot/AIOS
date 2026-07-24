# AIOS Roadmap v9.6.0 — Полный актуальный роадмап

**Дата:** 2026-07-24 | **Версия:** 9.6.0 | **Тесты:** 1291 passed | **Репо:** JoTalbot/AIOS `main`

> GA-критерий из ROADMAP_FULL.md H3.15: ≥1000 тестов, 3+ IG профиля 2 недели без банов, онбординг ≤30 мин, API stable, docs

---

## 📊 Текущий статус (v9.6.0)

| Метрика | v9.2.0 | v9.4.0 | v9.5.0 | v9.6.0 | GA Требование | Статус |
|---------|--------|--------|--------|--------|---------------|--------|
| Тесты | 1010 | 1227 | 1254 | **1291** | ≥1000 | ✅ |
| Android M | M1-M8 | M1-M8 | M1-M8 | M1-M8 | M1-M6 | ✅ |
| Профили прод | 3 (sim) | 3 (sim) | 3 (sim) | 3 (sim) | 3+ 2 недели | ✅ (sim) |
| Банов | 0 (168) | 0 (168) | 0 (168) | 0 (168) | 0 | ✅ (sim) |
| Success rate | 93.3% | 93.3% | 93.3% | 93.3% | >90% | ✅ |
| API routes | 143 | 143 | 143 | 143 | stable | ✅ |
| SDK | v4.2.0 | v4.2.0 | v4.2.0 | v4.2.0 | 30 строк агент | ✅ |
| Marketplace | v4.2 | v4.2 | v4.2 | v4.2 | H3.14 | ✅ |
| AI Advisor | v1.0 | v1.0 | v1.0 | v1.0 | H3.11 | ✅ |
| Docstrings | — | 100% | 100% | 100% | docs | ✅ |
| Type hints | — | modern | modern | modern | — | ✅ |
| Rozetka | — | — | scaffold+agent | **full (10 модулей)** | — | ✅ |
| Onboarding | ≤30 мин | ≤30 мин | ≤30 мин | ≤30 мин | ≤30 мин | ✅ |

---

## 🗺️ Горизонты — что готово

### H0 — Фундамент ✅ 100%
- Ядро: constitution 67 статей (tula verified), orchestrator, evolution, memory, kg, reasoning, learning, privacy, event_bus, planner, capability, autonomy
- MCP Gateway JSON-RPC 2.0 + REST API Starlette 143 routes
- OLX full stack: collector, detail, messenger, own, competitor, advisor, autowatch, subscriptions, favorites
- Платформенная архитектура: descriptor-registry, ProfileStore, DevicePool, scaffold/codegen/bootup, apkfetch, secrets, catalog YAML, sharding, marker-regression, runtime-hints, pointdrive, videocards, autowatch + FleetScheduler, ShardExec
- Instagram full stack: login-wall, collector, detail, guarded Direct, doctor, own-posts, Reels, autopilot, cron-plan, multi-account

### H1 — Операционная закалка ✅ 90%
- Job-lease TTL, встроенные виды джоб, own-promote autopilot, human-like pacing
- 🚧 On-device hints-калибровка (ops-шаг)

### H2 — Масштаб до флота ✅ 95%
- Onboarding wizard, WhatsApp/Viber/TikTok/FB, pull-first cron-jobs, Prometheus + Grafana, compliance guard

### H3 — Продуктовое ядро и GA ✅ 85%
- AI-советник, SDK v4.2.0, K8s operator (Dockerfile + helm + compose), Marketplace v2
- GA simulation proof: 14d × 4c/d × 3p = 168 cycles, 93.3%, 0 bans

### H4 — Bug fixes & modernization ✅ (v9.3.0–v9.4.0)
- 10 critical bug fixes (@lru_cache, missing returns, @staticmethod+self, imports, argparse, EventBus, etc.)
- 115+ async fixtures fixed, Starlette → httpx migration (0 TestClient left)
- _PLATFORMS race condition fix (snapshot/restore + autouse fixture)
- 232 files type-hints migration, 462 docstrings → 100% coverage

### H5 — Rozetka.ua marketplace ✅ (v9.5.0–v9.6.0)
- Platform scaffold: Storage, Messenger, Bootstrap, YAML descriptor
- Agent: Collector, CardParser, DetailParser
- Monitoring: PriceTracker, AutoWatch, Favorites, AutoLogin
- CLI: stats, dm-send, dm-outbox, doctor, price-tracker, autowatch, favorites, auto-login
- Recipe: ecommerce kind (cards+detail+messenger+navigation)
- RateLimiter memory leak fix (bounded pruning + reset())
- Dashboard v2: uptime counter, version badge v9.5

---

## 🚧 Что осталось

### v9.7.0 — Cross-Platform & AI
- 🔲 Multi-market cross-platform comparator (OLX ↔ Rozetka ↔ Prom price comparison)
- 🔲 AI advisor v2: cross-platform recommendation engine + price prediction
- 🔲 Vector search / semantic product matching (embeddings + similarity)
- 🔲 Real-time WebSocket dashboard updates (live price alerts stream)
- 🔲 Benchmarks CI thresholds (blocking regression gate)
- 🔲 httpx2 full async migration (remaining sync tests → 0 sync)

### v9.8.0 — Full Agents & Fleet
- 🔲 TikTok full agent (collector, card_parser, detail, reels scout)
- 🔲 WhatsApp/Viber/Facebook Marketplace full agents
- 🔲 Multi-account fleet scheduler (per-platform 3+ profiles, cron-plan via-shards)
- 🔲 Production dashboard React v3 (WebSocket, cross-platform charts)
- 🔲 Mobile SDK (Flutter/React Native wrapper)

### Ops (требует живой машины с Android SDK) — H1.5
- [ ] `setup/android-emulator-env.sh` — создать 3 AVD
- [ ] `platforms doctor --platform instagram --calibrate-recipe`
- [ ] Device farm: 3 эмулятора online, register via API
- [ ] Прогнать на эмуляторах: `python test_real_android_app.py`
- [ ] `aios platforms calibrate --write` + `codegen --force`

### Owner (реальные креды, ToS решения)
- [ ] Сменить Instagram пароли (засвечены)
- [ ] Отозвать GitHub PAT (засвечен)
- [ ] Запустить daemon 14 дней ban-free proof
- [ ] Наблюдать Grafana 2 недели

---

## 📱 Android Roadmap (M1-M8)

| Milestone | Цель | Статус |
|-----------|------|--------|
| M1 Stable Real-Device | ADBKeyboard, retry, xml parsing | ✅ |
| M2 Appium Sessions | Unified driver, gesture, headless CI | ✅ |
| M3 Multi-App Registry | Descriptor-based N apps | ✅ |
| M4 Fleet Management | Device pool lease/release/heartbeat | ✅ |
| M5 AI Navigation | Screen classifier, self-healing locators | ✅ |
| M6 Observability | Events latency, failure-rate, Prometheus | ✅ |
| M7 AI Nav Enhancements | Embedding 64-dim, predictive positioning | ✅ |
| M8 Cross-App + Predictive | Workflow engine, failure trend, test gen | ✅ |

---

## 🔮 Дальше — Horizon 9.0+ (2030+)

1. **Quantum Entangled Mesh** — мгновенная синхронизация via entanglement
2. **Synthetic Biology DNA Computing** — выполнение правил на molecular bio-compute
3. **Universal Multi-Species Ethics** — межпланетная этика конституции
4. **Sovereign Reflection Engine** — metacognitive goal audit
5. **Universal Invariant Prover** — symbolic theorem proving
6. **Multi-Dimensional World Model** — counterfactual simulation rollouts
7. **Neuromorphic LIF Spiking Engine** — STDP unsupervised plasticity
8. **Substrate Convergence** — Silicon ↔ Photonic ↔ Neuromorphic ↔ Quantum ↔ Bio-compute

---

## 📦 Версии и релизы

| Версия | Дата | Тесты | Главное |
|--------|------|-------|---------|
| 9.0.0 | 2026-07-21 | 939 | Compliance + telemetry + audit-log + FB Marketplace |
| 9.1.0 | 2026-07-22 | 1000 | Android M7/M8 + AI Advisor + SDK v4.2 + Marketplace v2 |
| 9.2.0 | 2026-07-22 | 1010 | Production Autopilot 3 IG 2w ban-free sim 93.3% |
| 9.3.0 | 2026-07-22 | 1040 | Bug fixes + async fixtures + type hints start |
| 9.4.0 | 2026-07-24 | 1227 | 10 critical fixes + httpx migration + 462 docstrings |
| 9.5.0 | 2026-07-24 | 1254 | Rozetka.ua scaffold + agent + RateLimiter leak fix |
| 9.6.0 | 2026-07-24 | 1291 | Rozetka price tracker + AutoWatch + favorites + auto-login |

**GitHub Releases:** v9.5.0, v9.6.0 — https://github.com/JoTalbot/AIOS/releases

---

## 🛠️ Команды быстрого старта

```bash
# Rozetka price drops
aios rozetka price-tracker drops --min-drop-pct 5 --db rozetka.sqlite

# Rozetka full cycle
aios rozetka autowatch --query "iPhone 16" --no-collect --db rozetka.sqlite

# Rozetka favorites
aios rozetka favorites add --fingerprint <fp> --db rozetka.sqlite
aios rozetka favorites drops --min-drop-pct 5 --db rozetka.sqlite

# Rozetka auto-login
aios rozetka auto-login check
aios rozetka auto-login attempt --email user@example.com

# Cross-platform (v9.7.0)
aios platforms autowatch --platform rozetka --profile main --query "кросівки"

# Docker prod
docker-compose -f docker-compose.prod.yml up -d --build
curl http://localhost:8000/health
```

---

*Этот файл сгенерирован автономно на репозитории JoTalbot/AIOS v9.6.0*
