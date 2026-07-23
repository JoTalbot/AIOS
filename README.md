# AIOS

![Version](https://img.shields.io/badge/version-9.3.0-blue)
![Tests](https://img.shields.io/badge/tests-1255%20passing-green)
![API](https://img.shields.io/badge/API-169%20routes-blue)
![Python](https://img.shields.io/badge/python-3.11%2B-blue)
![CI/CD](https://img.shields.io/badge/CI%2FCD-13%20workflows-green)

Self-evolving distributed operating system for application intelligence,
automated testing, API generation, skill evolution and collective learning.
Powered by the **Octopus Runtime**.

## 📚 Documentation

Full documentation at **[GitHub Pages](https://jotalbot.github.io/AIOS/)** or locally:

```bash
# MkDocs site
make docs-serve       # http://localhost:8000

# Sphinx PDF
make docs-pdf
```

Key docs:
- [Quick Start](docs/quickstart.md) — 30-minute onboarding
- [Production Exploitation](docs/PRODUCTION.md) — compliance, pacing, monitoring
- [Architecture](docs/architecture.md) — system design
- [Constitution](docs/constitution/INDEX.md) — 67 articles
- [Security](SECURITY.md) — deployment & secrets rotation checklist

## Components

| Component | Description | Status |
|-----------|-------------|--------|
| **Constitution Engine** | 67 articles, runtime decision pipeline | ✅ |
| **Orchestrator** | Sequential task execution | ✅ |
| **SQLite Persistence** | Audit, approvals, memory, knowledge graph | ✅ |
| **MCP Gateway** | JSON-RPC 2.0 tools/resources/prompts | ✅ |
| **REST API** | Starlette, 169 routes, bearer auth | ✅ |
| **Production Autopilot** | Compliance, pacing, predictive risk | ✅ |
| **AI Advisor** | Draft-only, human-approve, template registry | ✅ |
| **SDK v4.2.0** | Async/sync Python client, 25+ methods | ✅ |
| **Marketplace v2** | Publish & discover platform plugins | ✅ |
| **Data Export/Import** | JSON/CSV export of tasks, memory, audit, KG | ✅ |
| **Secret Manager** | API key generation, rotation, TTL, HMAC | ✅ |
| **Backup Manager** | Automated backups, compression, verification | ✅ |
| **Webhook System** | Event notifications (Slack/Teams/custom HTTP) | ✅ |
| **Web Dashboard** | Real-time monitoring (React) | ✅ |

## Quick start

```bash
# Install
pip install -r requirements.txt

# Test suite
python -m pytest -q

# Demo
python demo.py

# REST API
export AIOS_API_KEYS='{"my-key":{"subject":"dev","roles":["admin"]}}'
python run_rest_api.py --host 127.0.0.1 --port 8000
```

## Docker

```bash
# Development
docker-compose up -d --build

# Production (API + autopilot + Prometheus + Grafana)
docker-compose -f docker-compose.prod.yml up -d --build
```

## CLI

```bash
# Core
aios stats                           # System statistics
aios platforms list                  # List platforms
aios platforms scaffold --name prom  # Create platform skeleton

# Admin operations
aios admin export --type all --format json --output ./export
aios admin import --input data.json

# API key management
aios admin keys generate --subject user1 --roles admin --ttl 90
aios admin keys list
aios admin keys rotate --key <key> --ttl 90
aios admin keys health

# Backup management
aios admin backup create --label pre-deploy
aios admin backup list
aios admin backup verify --backup-id <id>
aios admin backup restore --backup-id <id>
aios admin backup health

# Webhook notifications
aios admin webhooks register --name slack --url https://hooks.slack.com/... --events ban_detected
aios admin webhooks list
aios admin webhooks notify --event ban_detected --data '{"profile":"ig_1"}' --severity critical
aios admin webhooks health
```

## API Endpoints (169 routes)

### Admin API (26 endpoints)

| Category | Key Endpoints |
|----------|--------------|
| **Export/Import** | `POST /api/v1/admin/export`, `POST /api/v1/admin/import` |
| **API Keys** | `POST /api/v1/admin/keys/generate`, `GET /api/v1/admin/keys`, `POST /api/v1/admin/keys/rotate`, `POST /api/v1/admin/keys/revoke` |
| **Backups** | `POST /api/v1/admin/backups`, `POST /api/v1/admin/backups/verify`, `POST /api/v1/admin/backups/restore` |
| **Webhooks** | `POST /api/v1/admin/webhooks`, `POST /api/v1/admin/webhooks/notify`, `GET /api/v1/admin/webhooks/health` |

All admin endpoints require `admin` role.

## Production Exploitation

```bash
# 2-week GA simulation
python run_production_autopilot.py --simulate-2weeks --verbose

# Daemon mode
python run_production_autopilot.py --daemon --interval 900

# Health check
python run_production_autopilot.py --health
```

## Monitoring & Alerts

```bash
# Prometheus metrics
curl http://localhost:8000/metrics

# Webhook metrics
aios admin webhooks health

# Grafana dashboards
open http://localhost:3000
```

## Supported Platforms

| Platform | Package | Status |
|----------|---------|--------|
| OLX.ua | ua.slando | ✅ Full stack |
| Instagram | com.instagram.android | ✅ Full stack |
| Facebook Marketplace | com.facebook.katana | ✅ Full stack |
| TikTok | com.zhiliaoapp.musically | ✅ Collector |
| Viber | com.viber.voip | ✅ Messaging |
| WhatsApp | com.whatsapp | ✅ Messaging |
| Prom.ua | com.prom.ua | ✅ Scaffold |
| Bigl.ua | com.bigl.ua | ✅ Scaffold |
| Shafa.ua | com.shafa.ua | ✅ Scaffold |

## CI/CD (13 workflows)

| Workflow | Purpose |
|----------|---------|
| `ci.yml` | Tests (Python 3.11-3.13) |
| `docs.yml` | GitHub Pages deploy |
| `docs-check.yml` | MkDocs strict build |
| `codeql.yml` | Security scanning |
| `docker.yml` | Multi-arch Docker + Trivy |
| `coverage.yml` | Codecov integration |
| `android.yml` | Android emulator tests |
| `full-ci-cd.yml` | Full CI/CD + deploy |
| `labeler.yml` | Auto-label PRs |
| `release-drafter.yml` | Auto release notes |
| `release.yml` | Release on tag |
| `stale.yml` | Auto-close stale issues |
| `secrets.yml` | Gitleaks secret scanning |

## Testing

```bash
# All tests
python -m pytest -q                    # Run the complete suite

# With coverage
python -m pytest --cov=aios_core

# Specific module
python -m pytest tests/test_webhook_manager.py -v
```

## Test status

The suite is executed in CI for supported Python versions. The last local audit
(2026-07-23, Python 3.13) completed successfully: **1255 passed**. One
`StarletteDeprecationWarning` remains and does not affect the test result. The
remediation history is recorded in
[`TEST_AUDIT_2026-07-23.md`](TEST_AUDIT_2026-07-23.md). Run the command above
before deployment.

## Security

Read [SECURITY.md](SECURITY.md) before deploying. Includes:
- Secrets rotation checklist (GitHub, Instagram, API keys, DB, Network)
- Role-based access control (viewer, writer, operator, approver, admin)
- Data isolation per API key subject
- TLS and reverse proxy requirements

## Project Stats

| Metric | Value |
|--------|-------|
| Version | 9.3.0 |
| Tests | 1255 collected; see test-status below |
| API routes | 169 |
| CLI commands | 35+ |
| Constitution articles | 67 |
| Platforms | 9 |
| CI/CD workflows | 13 |
| Core modules | ~250 |
| Documentation pages | 162+ |

## Contact

- **Owner:** JoTalbot <jo.talbot@gmail.com>
- **Repo:** [JoTalbot/AIOS](https://github.com/JoTalbot/AIOS)
- **Docs:** [GitHub Pages](https://jotalbot.github.io/AIOS/)
