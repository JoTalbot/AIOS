# AIOS Deployment Guide

## Docker Deployment (Recommended)

### Quick start with Docker Compose

```bash
cp .env.example .env
# Replace all placeholders in .env before deployment.
docker compose up -d --build
```

This starts:
- REST API on port 8000
- MCP server on port 8471
- SQLite persistence volume

### Manual Docker build

```bash
docker build -t aios .
docker run -p 8000:8000 \
  -e AIOS_API_KEYS='{"prod-key":{"subject":"admin","roles":["admin"]}}' \
  -v $(pwd)/aios.sqlite:/app/aios.sqlite \
  aios
```

## Environment Variables

| Variable          | Description                        | Default       |
|-------------------|------------------------------------|---------------|
| `AIOS_API_KEYS`   | JSON with API keys and roles       | Required      |
| `DB_PATH`         | SQLite database path               | `:memory:`    |

## Health & Monitoring

- `GET /health` — basic health check
- `GET /metrics` — Prometheus-compatible metrics
- Use `python monitor.py` for periodic checks

## Production Recommendations

- Always use TLS (reverse proxy)
- Use persistent volume for `aios.sqlite`
- Configure proper API keys
- Enable audit logging
- Run behind reverse proxy (nginx / traefik)

## Deployment Pipeline

All deployments follow the AIOS Evolution Manager pipeline:

### Stage 1: Proposal
Create and document the change proposal.

```python
from aios_core import EvolutionManager

manager = EvolutionManager()

change = {
    "component": "component_name",
    "description": "what is changing",
    "risk_level": "low|medium|high",
    "reversible": True/False
}

proposal = manager.create_proposal(change)
```

### Stage 2: Sandbox
Test the change in an isolated environment.

- Create sandbox environment
- Deploy change
- Run preliminary tests
- Document results

### Stage 3: Simulation
Run simulations to predict impact.

- Simulate with production data
- Test edge cases
- Verify performance
- Check compatibility

### Stage 4: Audit
Conducts security and compliance audit.

- Review code changes
- Security analysis
- Compliance check
- Risk assessment

### Stage 5: Approval
Require explicit approval to proceed.

```python
from aios_core import ApprovalManager

approver = ApprovalManager()
result = approver.request(change)

# Wait for approval
approver.approve(0)
```

### Stage 6: Deployment
Deploy to production.

- Backup current state
- Deploy changes
- Verify deployment
- Monitor for issues

## Rollback Procedure

If critical issues occur during deployment:

1. **Detection** - Monitor detects issue
2. **Isolation** - Affected component isolated
3. **Rollback** - Automatic rollback initiated
4. **Verification** - Verify system stability
5. **Investigation** - Analyze failure cause

## Monitoring Post-Deployment

- Monitor system health
- Track performance metrics
- Watch for anomalies
- Collect telemetry
- Log all activities

## Deployment Checklist

- [ ] Change proposal created
- [ ] Sandbox testing complete
- [ ] Simulations passed
- [ ] Audit passed
- [ ] Approval obtained
- [ ] Backup created
- [ ] Deployment executed
- [ ] Verification successful
- [ ] Monitoring enabled
- [ ] Documentation updated
