# AIOS Security Fix Report

## Critical Leaks Found & Actions Required

### 1. GitHub PAT Token Exposure
- **Status**: CRITICAL — must revoke immediately
- **Location**: Multiple README/ROADMAP files reference `ghp_LVgQ...`
- **Action**: 
  1. Go to github.com/settings/tokens → revoke the exposed token
  2. Generate new PAT with minimal scope
  3. Set as GitHub Actions secret, never in code

### 2. Instagram Credentials Exposure
- **Status**: CRITICAL — must change passwords immediately
- **Location**: Referenced in docs/config examples
- **Action**:
  1. Change all Instagram account passwords
  2. Move credentials to `.env` file (never commit)
  3. Add `.env` to `.gitignore` (already there)

### 3. Secret Rotation Checklist
```bash
# GitHub
git config --global credential.helper cache  # never store in git
export AIOS_API_KEYS='{"your-key":{"subject":"dev","roles":["admin"]}}'

# Instagram
export IG_PASSWORD_1='...'  # per-profile env vars
export IG_PASSWORD_2='...'

# API Keys  
aios admin keys generate --subject prod --roles operator --ttl 30
aios admin keys rotate --key <old-key> --ttl 30

# Database
# Use separate SQLite per profile, encrypt with sqlcipher in production
```

### 4. Code Scanning Results
- Run `gitleaks detect --source .` to find remaining secrets
- Run `bandit -r aios_core/` for Python security audit
- Both are in pre-commit hooks already

### 5. Network Security
- All API endpoints require bearer auth (`AIOS_API_KEYS`)
- CORS restricted to known origins
- Rate limiting active (100 req/min per IP)
- TLS required in production (reverse proxy)

### 6. Data Isolation
- Memory items scoped by `requester_id` (principal.subject)
- Personal category items invisible to non-owners
- Admin role bypasses isolation (documented)
- Each profile gets isolated SQLite DB

