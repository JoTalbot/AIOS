# Logging in AIOS

AIOS uses Python's `logging` module with structured output.

## Configuration

```python
from aios_core.logging_config import setup_logging

logger = setup_logging(level="DEBUG", log_file="aios.log")
```

## Log Levels

- `INFO` — normal operation
- `DEBUG` — detailed execution traces
- `WARNING` — potential issues
- `ERROR` — failures

## Log Format

```
2026-07-21 14:32:15 | INFO     | aios.orchestrator | Task created: analyze_data
```

Logs are written to both console and rotating file (`aios.log`).