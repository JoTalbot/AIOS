# Security and deployment

## Supported deployment posture

AIOS defaults to a **fail-closed** HTTP API. All endpoints except `GET /health`
require a bearer API key. The server returns `503` rather than becoming public
when no keys are configured.

Before starting either HTTP server, configure one or more keys outside source
control:

```bash
export AIOS_API_KEYS='{
  "replace-with-a-long-random-secret": {
    "subject": "operations",
    "roles": ["admin"]
  },
  "separate-reviewer-secret": {
    "subject": "reviewer-1",
    "roles": ["approver"]
  }
}'
python run_rest_api.py --host 127.0.0.1 --db /var/lib/aios/aios.sqlite
```

Use a secret manager, TLS and an authenticating reverse proxy in production.
API keys are deliberately a minimal service-to-service mechanism; they are not
a replacement for OIDC/mTLS, rotation, auditing or tenant-aware authorization.

## Roles

| Role | Access |
|---|---|
| `viewer` | Read-only endpoints |
| `writer` | Viewer access plus normal mutations |
| `operator` | Operational mutations, evolution and test execution |
| `approver` | Approval decisions only (and read access) |
| `admin` | All API operations |

`POST /api/v1/approvals/{id}/approve` and `/deny` require `approver` or `admin`.
Audit endpoints require `admin`.

## Data isolation

REST-created personal memory is bound to the authenticated API-key `subject`.
A non-admin subject cannot search, read, update or delete another subject's
personal records; direct MCP access to personal memory is deliberately disabled.
Tasks are likewise scoped to their creating subject. Existing owner-less
personal records from databases created before schema version 2 should be
reviewed and assigned an owner before production use.

## Important limitations

- Do **not** expose the services directly to the Internet.
- Bind to `127.0.0.1` by default and put a TLS reverse proxy in front of it.
- The built-in CORS policy is same-origin by default. Configure an explicit
  origin allowlist at your reverse proxy if browser access is needed.
- Use a persistent database path in production. The `:memory:` mode is only for
  tests and ephemeral demos.
- An approval is a governance record, not an automatic execution trigger. A
  production executor should bind an approved request to an immutable payload,
  authenticated reviewer and one-time execution token.

## Reporting vulnerabilities

Do not open public issues for suspected vulnerabilities. Contact the repository
maintainer privately with a minimal reproduction, affected revision and impact.
