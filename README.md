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

Access:
- Dashboard: http://localhost:8080
- API Docs: http://localhost:8080/docs
- Grafana: http://localhost:3000

## Documentation
- [Deployment Guide](docs/deployment_guide.md)
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
