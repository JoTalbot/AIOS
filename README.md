# AIOS - Self-Evolving Enterprise AI System

Production-ready AI orchestration platform with 10+ platform integrations, autonomous evolution, and enterprise-grade security.

## Features
- Self-evolving templates with A/B testing
- Massive Skills Library (240+ Octopus integrated skills)
- RAG-powered knowledge base (ChromaDB)
- ML conversion prediction
- 10+ platform adapters including Octopus MCPs (Browser Vision, Telegram Control, Arena Router)
- Enterprise security (JWT, API keys, audit logs)
- Kubernetes-ready with HPA and TLS
- Real-time observability (Prometheus, Grafana, Jaeger)

## Quick Start
```bash
git clone https://github.com/JoTalbot/AIOS.git
cd AIOS
docker-compose up -d
```

### SSH Server Deployment
To deploy AIOS to a VPS / dedicated server via SSH:
```bash
./scripts/deploy_ssh.sh <SSH_HOST> [SSH_USER] [SSH_PORT] [REMOTE_DIR] [BRANCH]
```
See [DEPLOY_SSH_RU.md](DEPLOY_SSH_RU.md) for full setup instructions (GitHub Actions & SSH scripts).

Access:
- Dashboard: http://localhost:8080
- API Docs: http://localhost:8080/docs
- Grafana: http://localhost:3000

## Multi-machine and multi-agent coordination

AIOS is maintained from multiple machines by people and different AI agents, sometimes in parallel.
Before editing, read [AGENTS.md](AGENTS.md),
[the coordination protocol](coordination/README.md), and
[the current project context](coordination/PROJECT_CONTEXT.md). Every work session must leave a
separate handoff journal so unfinished work and its next step survive machine or agent changes.

## Documentation
- [Current generated project inventory](docs/PROJECT_INVENTORY.md)
- [Deployment Guide (RU)](DEPLOY_GUIDE_RU.md)
- [SSH Deployment Guide (RU)](DEPLOY_SSH_RU.md)
- [Deployment Guide (EN)](docs/deployment_guide.md)
- [Evolution Engine](docs/evolution.md)
- [ML & RAG](docs/ml_and_recommendations.md)
- [Security](docs/security.md)
- [Pitch Deck](docs/pitch_deck.md)

## Contact
JoTalbot | jo.talbot@gmail.com

## License
MIT License

## Octopus Telemetry & Ops Update (v16.2+)
AIOS now includes the advanced `octopus_obs` (Grafana dashboards, Prometheus alerts) and `octopus_ops` (Fly.io stack configurations, Execution Policies) enabling massive batch processing of parallel agent waves.
