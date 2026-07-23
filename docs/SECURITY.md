# Security and deployment

**Версия документа:** 9.2.0 | **Дата:** 23 июля 2026

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

---

## 🔒 Чек-лист безопасности (Secrets Rotation Checklist)

Выполните перед production-развёртыванием и при любом подозрении на компрометацию.

### GitHub

- [ ] **Отозвать все ранее засвеченные GitHub PAT** (`ghp_*`):
  - Settings → Developer settings → Personal access tokens → Revoke
  - Создать новый PAT с минимальными правами: `repo` scope только
  - Хранить в secret manager (не в `.env`, не в git history)
- [ ] **Проверить git history на секреты:**
  ```bash
  git log --all --diff-filter=D --name-only | grep -i '\.env\|secret\|credential'
  git filter-branch --force --index-filter \
    "git rm --cached --ignore-unmatch .env secrets.json" \
    --prune-empty --tag-name-filter cat -- --all
  ```
- [ ] **Включить 2FA** для всех контрибьюторов
- [ ] **Branch protection rules** на `main`: required reviews, no force push

### Instagram / Соцсети

- [ ] **Сменить пароли** всех IG-аккаунтов, использовавшихся в тестах
  - Settings → Security → Password → Change
  - Использовать уникальный пароль (менеджер паролей)
- [ ] **Отозвать все активные сессии:**
  - Settings → Security → Login Activity → Log out all
- [ ] **Включить 2FA** (authenticator app, не SMS)
- [ ] **Проверить connected apps** и отозвать ненужные
- [ ] **Review API access** — отозвать старые токены

### API Keys (AIOS)

- [ ] **Сгенерировать новые API-ключи:**
  ```bash
  # Генерация случайного ключа
  python -c "import secrets; print(secrets.token_urlsafe(48))"
  ```
- [ ] **Ротация ключей каждые 90 дней** (настройка cron/CI)
- [ ] **Хранить в secret manager:**
  - AWS Secrets Manager / HashiCorp Vault / GCP Secret Manager
  - НЕ в `.env` файлах в репозитории
  - НЕ в переменных окружения CI/CD в открытом виде
- [ ] **Минимальные привилегии:** каждый ключ — только необходимые роли

### Database

- [ ] **Production DB** — отдельная от dev/test (`/var/lib/aios/aios.sqlite`)
- [ ] **Шифрование at rest:**
  ```bash
  # LUKS для Linux
  cryptsetup luksFormat /dev/sdX
  ```
- [ ] **Backup** с шифрованием, регулярный (cron + offsite)
- [ ] **WAL mode** для SQLite: `PRAGMA journal_mode=WAL;`
- [ ] **Review** personal records — assign owners (schema v2+)

### Network / Infrastructure

- [ ] **TLS обязательно:**
  - Let's Encrypt (certbot) или managed certificate
  - `nginx` / `caddy` reverse proxy
  - HSTS header: `Strict-Transport-Security: max-age=31536000`
- [ ] **Bind только на 127.0.0.1:**
  ```bash
  python run_rest_api.py --host 127.0.0.1 --port 8000
  ```
- [ ] **Firewall rules:** только порты 443 (HTTPS) наружу
- [ ] **Docker network:** `internal: true` для backend-сервисов
- [ ] **Rate limiting** на reverse proxy (100 req/min per IP)

### Monitoring & Alerting

- [ ] **Prometheus + Grafana** — production dashboards
- [ ] **Alerts:** BanDetected, LowSuccessRate, DeviceOffline
- [ ] **Audit log:** все действия записываются в `aios_audit` таблицу
- [ ] **Log rotation:** `logrotate` или Docker logging driver с max-size
- [ ] **SIEM интеграция** (опционально): отправка audit events

### Production Checklist

- [ ] Все секреты в secret manager
- [ ] TLS настроен
- [ ] Reverse proxy (nginx/caddy) перед AIOS
- [ ] Docker resource limits установлены (2 CPU, 2 GB)
- [ ] Health check настроен (`/health` every 30s)
- [ ] Database backups automated
- [ ] Alerts tested (fire test alert, verify notification)
- [ ] 14-day ban-free simulation passed (`ga_met: true`)
- [ ] Onboarding checklist выполнен (≤30 мин)
- [ ] Documentation reviewed and up-to-date

---

## Reporting vulnerabilities

Do not open public issues for suspected vulnerabilities. Contact the repository
maintainer privately with a minimal reproduction, affected revision and impact.

**Контакт:** jo.talbot@gmail.com (PGP key available on request)

## Security audit history

| Дата | Тип | Результат |
|------|-----|-----------|
| 2026-07-20 | Internal audit | See SECURITY_AUDIT_REPORT.md |
| 2026-07-22 | Production simulation | 168 cycles, 0 bans |
| 2026-07-23 | Documentation update | Secrets rotation checklist added |
