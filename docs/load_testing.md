# Load Testing with Locust

## Install
```bash
pip install locust
```

## Run Tests
```bash
locust -f load_tests/locustfile.py
```

## Web Interface
Open http://localhost:8089

Configure:
- Number of users: 100
- Spawn rate: 10 users/sec
- Host: http://localhost:8080

## Scenarios
1. **AIOSUser** (weight 3): General API usage
2. **WebhookUser** (weight 1): High-frequency webhooks

## Metrics
- Response time (p50, p95, p99)
- Requests per second
- Failure rate
