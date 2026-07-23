# AIOS

![Version](https://img.shields.io/badge/version-9.2.0--production-blue)
![Tests](https://img.shields.io/badge/tests-1010%20passing-green)
![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![License](https://img.shields.io/badge/license-proprietary-orange)

Self-evolving distributed operating system for application intelligence,
automated testing, API generation, skill evolution and collective learning.
Powered by the **Octopus Runtime**.

## 📚 Documentation

Full documentation is available at **[GitHub Pages](https://jotalbot.github.io/AIOS/)** or locally:

```bash
# MkDocs site (recommended)
pip install mkdocs mkdocs-material mkdocs-minify-plugin
mkdocs serve          # http://localhost:8000

# Sphinx PDF
pip install sphinx sphinx-rtd-theme
cd docs/source && make latexpdf
```

Key docs:
- [Quick Start](docs/quickstart.md) — 30-minute onboarding
- [Production Exploitation](docs/PRODUCTION.md) — compliance, pacing, monitoring
- [Architecture](docs/architecture.md) — system design
- [Constitution](docs/constitution/INDEX.md) — 67 articles
- [Security](SECURITY.md) — deployment & secrets rotation checklist

## Components

- **Constitution and policies** — 67 articles, rule loading and runtime decision pipeline
- **Orchestrator** — sequential task execution with constitutional evaluation
- **SQLite persistence** — audit events, approvals, memory, knowledge graph and evolution records
- **MCP gateway** — JSON-RPC 2.0 tool/resource/prompt interface
- **REST API** — Starlette application, 143 routes, bearer auth
- **Production Autopilot** — industrial exploitation with compliance, pacing, predictive risk
- **AI Advisor** — intelligent advisor with draft-only mode and human-approve
- **SDK v4.2.0** — official Python client (async + sync, 25+ methods)
- **Marketplace v2** — publish and discover platform plugins
- **Web Dashboard** — real-time monitoring (React)

## Quick start (development)

```bash
python -m pip install -r requirements.txt
python -m pytest -q
python demo.py
```

## Docker (recommended)

```bash
docker-compose up -d --build
curl http://localhost:8000/health
curl http://localhost:8000/metrics
```

## Production Exploitation

```bash
# 2-week GA simulation (3 IG profiles, 168 cycles)
python run_production_autopilot.py --simulate-2weeks --cycles-per-day 24 --verbose

# Daemon mode (real exploitation)
python run_production_autopilot.py --daemon --interval 900

# Docker production (API + autopilot + Prometheus + Grafana)
docker-compose -f docker-compose.prod.yml up -d --build
```

See [Production Exploitation Guide](docs/PRODUCTION.md) for details.

## Monitoring

```bash
# CLI monitor
python monitor.py --url http://localhost:8000 --interval 30

# Prometheus metrics
curl http://localhost:8000/metrics

# Grafana dashboards (production)
open http://localhost:3000
```

## REST API (requires authentication)

```bash
export AIOS_API_KEYS='{"local-development-key":{"subject":"developer","roles":["admin"]}}'
python run_rest_api.py --host 127.0.0.1 --port 8000 --db ./aios.sqlite
curl -H 'Authorization: Bearer local-development-key' http://127.0.0.1:8000/api/v1/stats
```

For the standalone MCP HTTP endpoint:

```bash
export AIOS_API_KEYS='{"local-development-key":{"subject":"developer","roles":["admin"]}}'
python run_mcp_server.py --host 127.0.0.1 --port 8471 --db ./aios.sqlite
```

`GET /health` is public. Every other HTTP endpoint fails closed with `503` if
no API keys are configured and responds with `401` without a valid bearer key.

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

## Testing

```bash
python -m pytest -q
```

The suite covers persistence, constitutional policy, orchestration, MCP,
REST, evolution state transitions, production autopilot and API security regressions.

**Current:** 1010 tests, 997 passed (13 require real Android devices).

## Security

Read [SECURITY.md](SECURITY.md) before deploying. In particular, use TLS, a
secret manager, a persistent database and a reverse proxy; do not bind a
production service directly to a public interface.

**Secrets rotation checklist** included — covers GitHub PAT, Instagram credentials,
API keys, database encryption and network security.

## Status

| Metric | Value |
|--------|-------|
| Version | 9.2.0-production |
| Tests | 1010 (997 passed) |
| API routes | 143 |
| Constitution | 67 articles |
| Platforms | 9 supported |
| Android milestones | M1–M8 ✅ |
| SDK | v4.2.0 |
| Marketplace | v2 |
| Production sim | 14d / 3 profiles / 0 bans / 93.3% success |

## Contact

- **Owner:** JoTalbot <jo.talbot@gmail.com>
- **Repo:** [JoTalbot/AIOS](https://github.com/JoTalbot/AIOS)
- **Docs:** [GitHub Pages](https://jotalbot.github.io/AIOS/)
