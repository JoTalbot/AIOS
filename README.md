# AIOS

![Version](https://img.shields.io/badge/version-10.15.0-blue)
![Tests](https://img.shields.io/badge/tests-1255%20passed%20(local%20audit)-green)
![API](https://img.shields.io/badge/API-169%20routes-blue)
![Python](https://img.shields.io/badge/python-3.11%2B-blue)
![CI/CD](https://img.shields.io/badge/CI%2FCD-15%20workflows-green)

**A**pplication **I**ntelligence **O**perating **S**ystem — a self-evolving
distributed platform for multi-platform marketplace automation, AI-assisted
decision pipelines, and collective learning across agents.

Built with the **Octopus Runtime** at its core, AIOS provides:

- **Multi-platform automation** — OLX, Instagram, Facebook, TikTok, WhatsApp,
  Viber, Prom, Bigl, Shafa and any custom platform via YAML descriptors
- **Constitution-gated execution** — 67 constitutional articles enforced at
  runtime through a compliance pipeline before any action
- **Device pool & shard routing** — lease emulators/physical devices, route
  profiles across hosts with sticky HRW hashing
- **Collective intelligence** — agent swarms, evolution engines, MCP Gateway
  (JSON-RPC 2.0), and federated knowledge graphs
- **Production autopilot** — pacing, predictive risk scoring, webhook alerts,
  and full daemon-mode operation

---

## 📚 Documentation

Full documentation at **[GitHub Pages](https://jotalbot.github.io/AIOS/)** or locally:

```bash
# MkDocs site
make docs-serve       # http://localhost:8000

# Sphinx PDF
make docs-pdf
```

Key docs:
| Document | Description |
|----------|-------------|
| [Quick Start](docs/quickstart.md) | 30-minute onboarding |
| [Architecture](ARCHITECTURE.md) | System design & data flow |
| [Production Exploitation](PRODUCTION_EXPLOITATION.md) | Compliance, pacing, monitoring |
| [Constitution](docs/constitution/INDEX.md) | 67 articles governing all AI decisions |
| [Security](SECURITY.md) | Deployment & secrets rotation checklist |
| [Contributing](CONTRIBUTING.md) | Development workflow & standards |
| [Changelog](CHANGELOG.md) | Version history |

---

## 🏗️ Architecture

```
AIOS/
├── aios_core/            # Core engine (273-line app.py!)
│   ├── api/              #   REST API — routes.py + 4 handler mixins
│   ├── container.py      #   DI container (sync + async services)
│   ├── config_central.py #   YAML config with env overrides
│   ├── async_bus.py      #   Non-blocking event bus
│   ├── async_core.py     #   Async DB + KG wrappers
│   └── modules/          #   9 platform modules
├── aios_mcp/             # ✨ Standalone MCP Gateway package
├── aios_cli/             # CLI sub-commands (olx, platforms, instagram, messengers)
├── aios_cli.py           # Entry point (281 lines)
├── platforms/            # YAML descriptors per platform
├── tests/                # 220 test files, 3,688 test functions
├── docs/                 # 162+ documentation pages
├── deploy/ helm/ k8s/    # Deployment manifests
└── tools/                # quality_check.py, scripts
```

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

---

## 🚀 Quick start

### Prerequisites

- **Python** 3.11 or later
- **ADB** (Android Debug Bridge) — for device automation
- **SQLite** 3.35+ — included with Python
- **Docker** (optional) — for containerised deployment

### Install

```bash
git clone git@github.com:JoTalbot/AIOS.git
cd AIOS
pip install -r requirements.txt

# Optional: install pre-commit hooks
pre-commit install
```

### Verify

```bash
# Run the test suite (latest local audit: 1255 passed)
python -m pytest -q

# Run the demo
python demo.py

# Start REST API
export AIOS_API_KEYS='{"my-key":{"subject":"dev","roles":["admin"]}}'
python run_rest_api.py --host 127.0.0.1 --port 8000

# Start Web Dashboard
python run_dashboard.py --port 8080
```

---

## 🐳 Docker

```bash
# Development
cp .env.example .env
# Replace every placeholder in .env before starting containers.
docker compose up -d --build

# Production (API + autopilot + Prometheus + Grafana)
cp .env.example .env
# Set AIOS_API_KEYS and GRAFANA_PASSWORD to unique secrets in .env.
docker compose -f docker-compose.prod.yml up -d --build
```

---

## 🖥️ CLI

```bash
# Core
aios stats                           # System statistics
aios platforms list                  # List registered platforms
aios platforms scaffold --name prom  # Create a new platform skeleton

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

---

## 📡 API Endpoints (169 routes)

### Admin API (26 endpoints)

| Category | Key Endpoints |
|----------|--------------|
| **Export/Import** | `POST /api/v1/admin/export`, `POST /api/v1/admin/import` |
| **API Keys** | `POST /api/v1/admin/keys/generate`, `GET /api/v1/admin/keys`, `POST /api/v1/admin/keys/rotate`, `POST /api/v1/admin/keys/revoke` |
| **Backups** | `POST /api/v1/admin/backups`, `POST /api/v1/admin/backups/verify`, `POST /api/v1/admin/backups/restore` |
| **Webhooks** | `POST /api/v1/admin/webhooks`, `POST /api/v1/admin/webhooks/notify`, `GET /api/v1/admin/webhooks/health` |

All admin endpoints require `admin` role.

---

## 🔧 Development

### Code quality

```bash
# Run all quality checks
make quality

# Type checking (incremental adoption)
make typecheck

# Format code
black aios_core/
isort aios_core/
```

### Project structure

```
AIOS/
├── aios_core/            # Core engine — agents, constitution, API, platform logic
│   ├── api/              # REST API (Starlette)
│   ├── modules/          # Platform modules (olx, instagram, whatsapp, …)
│   ├── platforms/        # Platform descriptors, resolvers, device pool
│   └── test_engine/      # Test runner & suites
├── platforms/            # YAML descriptors per marketplace platform
├── tests/                # Test suite (unit, integration, e2e, load, security)
├── docs/                 # MkDocs documentation source
├── deploy/               # Deployment scripts
├── helm/                 # Kubernetes Helm charts
├── k8s/                  # Raw Kubernetes manifests
├── scripts/              # Utility & maintenance scripts
├── tools/                # External tool integrations
└── web_ui/               # React dashboard frontend
```

### Adding a new platform

1. Create a YAML descriptor: `platforms/<name>.yaml`
2. Scaffold from APK: `aios platforms from-apk path/to/app.apk --name my-platform`
3. Calibrate parser hints: `aios platforms calibrate --platform my-platform --dump dump.xml`
4. Generate the parser: `aios platforms codegen --platform my-platform`
5. Run bootup pipeline: `aios platforms bootup --name my-platform --package com.example.app`
6. Write tests in `tests/test_<platform>.py`
7. Add compliance flags and update docs

See [CONTRIBUTING.md](CONTRIBUTING.md) for the full development workflow.

---

## 🏭 Production Exploitation

```bash
# 2-week GA simulation
python run_production_autopilot.py --simulate-2weeks --verbose

# Daemon mode
python run_production_autopilot.py --daemon --interval 900

# Health check
python run_production_autopilot.py --health
```

---

## 📊 Monitoring & Alerts

```bash
# Prometheus metrics
curl http://localhost:8000/metrics

# Webhook metrics
aios admin webhooks health

# Grafana dashboards
open http://localhost:3000
```

---

## 📱 Supported Platforms

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

---

## 🔄 CI/CD (13 workflows)

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

---

## 🧪 Testing

```bash
# All tests
python -m pytest -q

# With coverage
python -m pytest --cov=aios_core

# Specific module
python -m pytest tests/test_webhook_manager.py -v

# Skip real-device tests
python -m pytest -q -k "not real_device"
```

### Test status

The suite is executed in CI for supported Python versions. The last local audit
(2026-07-23, Python 3.13) completed successfully: **1255 passed**. One
`StarletteDeprecationWarning` remains and does not affect the test result. The
remediation history is recorded in
[`TEST_AUDIT_2026-07-23.md`](TEST_AUDIT_2026-07-23.md). Run the command above
before deployment.

---

## 🔒 Security

Read [SECURITY.md](SECURITY.md) before deploying. Includes:
- Secrets rotation checklist (GitHub, Instagram, API keys, DB, Network)
- Role-based access control (viewer, writer, operator, approver, admin)
- Data isolation per API key subject
- TLS and reverse proxy requirements

---

## 📈 Project Stats

| Metric | Value |
|--------|-------|
| Version | 10.15.0 |
| Tests | 1255 passed in the latest local audit |
| API routes | 169 |
| CLI commands | 35+ |
| Constitution articles | 67 |
| Platforms | 9 |
| CI/CD workflows | 15 |
| Core modules | ~250 |
| Documentation pages | 168 |

---

## 👥 Contact

- **Owner:** JoTalbot <jo.talbot@gmail.com>
- **Repo:** [JoTalbot/AIOS](https://github.com/JoTalbot/AIOS)
- **Docs:** [GitHub Pages](https://jotalbot.github.io/AIOS/)
- **Contributing:** [CONTRIBUTING.md](CONTRIBUTING.md)
- **Security:** [SECURITY.md](SECURITY.md)
