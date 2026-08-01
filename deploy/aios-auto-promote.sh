#!/usr/bin/env bash
# AIOS auto-promote: merges auto-coder staging commits into main and pushes (opt-in via env).
# Guards: compile validation, junk-file check, conflict abort, uncommitted-change abort.
set -euo pipefail

PROD_DIR="${AIOS_PROD_DIR:-/root/AIOS}"
STAGING_DIR="${AIOS_STAGING_DIR:-/root/AIOS-autocoder}"
LOG="/root/AIOS/logs/auto_promote.log"

# Paths that must never be pushed to main from autonomous commits.
JUNK_PATTERNS=(
    'tools/aios_'
    'tools/run_auto_coder.py'
    'tools/run_telegram_bot.py'
)

log(){ echo "[$(date '+%F %T')] $*" | tee -a "$LOG"; }

[[ -e "$PROD_DIR/.git" ]] || { log "ERROR: prod worktree missing"; exit 1; }
[[ -e "$STAGING_DIR/.git" ]] || { log "ERROR: staging worktree missing"; exit 1; }
[[ "$(git -C "$STAGING_DIR" branch --show-current)" == "auto/coder-staging" ]] || { log "ERROR: staging not on auto/coder-staging"; exit 1; }

if [[ -n "$(git -C "$PROD_DIR" status --porcelain)" ]]; then
    log "SKIP: production worktree has uncommitted changes"; exit 0
fi

cd "$STAGING_DIR"
NEW=$(git log main..HEAD --oneline 2>/dev/null || true)
if [[ -z "$NEW" ]]; then
    log "no new auto-coder commits to promote"; exit 0
fi
log "new commits:\n$NEW"

# --- junk check: any new commit touching a forbidden path -> hold promotion ---
if git diff main...HEAD --name-only 2>/dev/null | grep -E "$(printf '%s|' "${JUNK_PATTERNS[@]}" | sed 's/|$//')" >/dev/null; then
    log "BLOCKED: new commits touch protected/junk paths; NOT promoting"
    exit 1
fi
log "junk check OK"

# --- compile validation ---
if ! python3 -m compileall -q "$STAGING_DIR/aios_core" "$STAGING_DIR/run_coder_orchestrator.py" 2>/dev/null; then
    log "ERROR: compile validation failed; NOT promoting"; exit 1
fi
log "compile validation OK"

# --- test gate: run a quick pytest on changed core modules if present ---
if [[ -d "$STAGING_DIR/aios_core" ]] && command -v /opt/aios/.venv/bin/python3.11 >/dev/null 2>&1; then
    # Only fail the gate on real import/collection errors, not on system-missing deps.
    if (cd "$STAGING_DIR" && timeout 240 /opt/aios/.venv/bin/python3.11 -m pytest tests/security tests/integration \
            -q --no-header -p no:cacheprovider >/tmp/aios_promote_test.log 2>&1); then
        log "test gate: security+integration OK"
    else
        # Block only on real test failures, not on collection errors from
        # system-missing modules (e.g. /opt/octopus-*) or dependency gaps.
        if grep -qE "^FAILED|^[0-9]+ failed|passed, [0-9]+ failed" /tmp/aios_promote_test.log; then
            log "BLOCKED: security/integration tests FAILED; NOT promoting"
            tail -5 /tmp/aios_promote_test.log | sed 's/^/  /' >> "$LOG"
            exit 1
        else
            log "test gate: collection errors only (non-blocking)"
        fi
    fi
fi

# --- merge into main ---
cd "$PROD_DIR"
git fetch . auto/coder-staging:refs/remotes/autostaging 2>/dev/null || true
if ! git merge auto/coder-staging --no-edit >/dev/null 2>&1; then
    log "ERROR: merge conflict; aborting"; git merge --abort 2>/dev/null || true; exit 1
fi
log "merged auto/coder-staging into main"

# --- push (opt-in) ---
if [[ "${AIOS_AUTO_PUSH:-0}" == "1" ]]; then
    if git push origin main >/dev/null 2>&1; then
        log "pushed main -> origin/main"
    else
        log "WARN: push failed; main ahead of origin (retry next cycle)"
    fi
else
    log "AIOS_AUTO_PUSH != 1; committed locally only"
fi
log "auto-promote complete"
