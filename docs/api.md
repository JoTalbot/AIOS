# API Reference

The interactive, runtime-generated contract is available from a running server:

- Swagger UI: [`/docs`](http://127.0.0.1:8000/docs)
- OpenAPI JSON: [`/openapi.json`](http://127.0.0.1:8000/openapi.json)

`/openapi.json` is reconciled with the registered Starlette routes at runtime,
so it includes every HTTP endpoint. Curated routes have detailed schemas;
generated entries use a generic successful response until a dedicated schema is
added.

## Authentication and roles

All operational REST endpoints require:

```http
Authorization: Bearer <AIOS API key>
```

Public endpoints are limited to `GET /health`, `/docs`, and `/openapi.json`.
The WebSocket endpoint `/ws` also requires the bearer header during its upgrade.

| Role | Access |
|---|---|
| `viewer` | Read-only API endpoints |
| `writer` | Viewer access plus normal mutations |
| `operator` | Operational mutations, evolution and test execution |
| `approver` | Approval decisions |
| `admin` | Administrative API, audit, backups, key and webhook management |

## Core endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Public health check |
| `GET` | `/metrics` | Prometheus metrics (authenticated) |
| `GET` | `/api/v1/stats` | System statistics |
| `POST` | `/api/v1/tasks` | Create a task |
| `GET` | `/api/v1/tasks` | List tasks visible to the subject |
| `POST` | `/api/v1/evaluate` | Constitutional evaluation |
| `GET/POST` | `/api/v1/memory` | Search or store memory |
| `GET` | `/api/v1/audit` | Audit records (`admin`) |

## Administrative API

All `/api/v1/admin/*` endpoints require the `admin` role. Major groups:

- `POST /api/v1/admin/export`, `POST /api/v1/admin/import`
- `/api/v1/admin/keys/*` — generate, list, rotate and revoke API keys
- `/api/v1/admin/backups/*` — create, list, verify, restore and clean backups
- `/api/v1/admin/webhooks/*` — manage webhook targets and delivery history

For production, set `AIOS_ADMIN_DATA_DIR` to confine Admin API import/export
paths to a dedicated directory. Input and output paths outside this directory
are rejected.

## Python SDK

```python
from aios_sdk import AIOSClient

client = AIOSClient("http://localhost:8000", api_key="replace-with-a-real-key")
stats = await client.stats()
```

## CLI

```bash
aios run
aios dashboard
aios demo
aios stats
```
