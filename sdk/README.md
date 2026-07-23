# AIOS Python SDK v4.2.0

Official Python client for the [AIOS](https://github.com/JoTalbot/AIOS) REST API.

## Install

```bash
pip install aios-client
```

## Quick Start

```python
import asyncio
from aios_sdk import AIOSClient

async def main():
    client = AIOSClient("http://localhost:8000", api_key="your-api-key")

    # System stats
    stats = await client.stats()
    print(f"Version: {stats.get('version')}")

    # OLX — collect ads
    result = await client.olx_collect(query="iphone", max_cards=50)
    print(f"Collected: {result}")

    # OLX — market statistics
    market = await client.olx_stats(query="iphone")
    print(f"Min price: {market.get('min_price')}, Avg: {market.get('avg_price')}")

asyncio.run(main())
```

## Features

- **Async-first** — built on `httpx.AsyncClient`
- **Sync available** — `AIOSSyncClient` for scripts
- **All 85+ endpoints** — OLX, Devices, Shards, Profiles, Advisor, ...
- **Bearer auth** — pass `api_key` or `AIOS_API_KEY` env var
- **WebSocket** — real-time streaming
- **Marketplace** — publish/discover platform plugins

## API Reference

| Method | Description |
|--------|-------------|
| `stats()` | System statistics |
| `health()` | Health check |
| `olx_collect(query, max_cards)` | Collect OLX ads |
| `olx_stats(query)` | OLX market statistics |
| `olx_history(fingerprint)` | Price history |
| `olx_drops(query)` | Price drops |
| `devices_list()` | Device pool status |
| `platforms_list()` | Registered platforms |
| `profiles_list(platform)` | Platform profiles |
| `advisor_draft(...)` | AI advisor reply draft |
| `constitution_stats()` | Constitution statistics |

See [OpenAPI docs](http://localhost:8000/docs) for the full 85-endpoint reference.

## License

MIT — JoTalbot
