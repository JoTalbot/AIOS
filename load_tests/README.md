# Load Testing with Locust

## Install
```bash
pip install locust
```

## Run
```bash
locust -f load_tests/locustfile.py
```

Open http://localhost:8089 and configure:
- Number of users: 100
- Spawn rate: 10
- Host: http://localhost:8080

## Scenarios
- **AIOSUser**: General API usage (health, platforms, features, GraphQL)
- **WebhookUser**: High-frequency webhook simulation
