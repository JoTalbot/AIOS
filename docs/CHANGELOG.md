# Changelog

## v9.2.0-production (2026-07-23)

### Documentation
- ✅ MkDocs site created (`mkdocs.yml`) — Material theme, full navigation for 162 markdown files
- ✅ Sphinx updated to v9.2.0 — all core modules documented, PDF-ready
- ✅ `PRODUCTION.md` — complete Production Exploitation Guide
- ✅ `quickstart.md` — 30-minute onboarding guide
- ✅ `SECURITY.md` — secrets rotation checklist added
- ✅ `SECURITY_AUDIT_REPORT.md` — documentation audit section added
- ✅ `docs/index.md` — updated to v9.2.0-production
- ✅ `requirements.txt` — MkDocs dependencies added

### Production Exploitation (v9.2.0)
- Production Autopilot: 3 IG profiles, 14-day simulation, 93.3% success, 0 bans
- docker-compose.prod.yml: API + autopilot daemon + dashboard + Prometheus + Grafana
- production-alerts.yml: 8 alert rules (BanDetected, LowSuccessRate, etc.)
- grafana-production.json: 9 panels
- PRODUCTION_EXPLOITATION.md: 400+ lines
- 10 new tests (1010 total)

### Previous: v9.1.0 (2026-07-22)
- Android M7 fixed + M8 cross-app predictive test-gen (16 tests)
- AI Advisor: template registry per platform, intent classification, price advice
- SDK v4.2.0: async/sync client, 25+ methods, 6 tests
- Marketplace v2: capability + platform plugins, 8 tests
- Docker production ready

### Previous: v9.0.0 (2026-07-21)
- Constitution: 67/67 articles verified
- Compliance + telemetry + audit-log
- FB Marketplace integration
- OLX full stack: collector, detail, messenger, own, competitor, advisor, autowatch, subscriptions, favorites
- Platforms scaling architecture (10000+ apps)
- 939 tests passing

### Earlier Versions
See [CHANGELOG.md](../CHANGELOG.md) in repository root for complete history.
