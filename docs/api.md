# API Reference

## REST Endpoints

- `GET /health`
- `GET /metrics`
- `GET /api/v1/stats`
- `POST /api/v1/tasks`
- `POST /api/v1/evaluate`
- `POST /api/v1/evolution/proposals`

## Python SDK

```python
from aios_sdk import AIOSClient

client = AIOSClient("http://localhost:8000")
stats = await client.stats()
```

## CLI

```bash
aios run
aios dashboard
aios demo
aios stats
```
