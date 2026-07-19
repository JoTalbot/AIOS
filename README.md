# AIOS

Self-evolving distributed operating system for application intelligence,
automated testing, API generation, skill evolution and collective learning.
Powered by the Octopus Runtime.

## Components

- **Constitution and policies** — rule loading and runtime decision pipeline.
- **Orchestrator** — sequential task execution with constitutional evaluation.
- **SQLite persistence** — audit events, approvals, memory, knowledge graph and
evolution records.
- **MCP gateway** — JSON-RPC 2.0 tool/resource/prompt interface.
- **REST API** — Starlette application exposing runtime subsystems.

## Quick start (development)

```bash
python -m pip install -r requirements.txt
python -m pytest -q
python demo.py
```

Run a local REST service (requires authentication by default):

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

## Testing

```bash
python -m pytest -q
```

The suite covers persistence, constitutional policy, orchestration, MCP,
REST, evolution state transitions and API security regressions.

## Security

Read [SECURITY.md](SECURITY.md) before deploying. In particular, use TLS, a
secret manager, a persistent database and a reverse proxy; do not bind a
production service directly to a public interface.
