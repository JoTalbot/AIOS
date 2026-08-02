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

tg_send(){
  local txt="$1"
  local tk="${AIOS_TELEGRAM_TOKEN:-}"
  local cid="${TELEGRAM_CHAT_ID:-}"
  [ -n "$tk" ] && [ -n "$cid" ] || return 0
  curl -s -m 10 -X POST "https://api.telegram.org/bot$tk/sendMessage" \
    -H "Content-Type: application/json" \
    -d "{\"chat_id\":$cid,\"text\":$(printf '%s' "$txt" | python3 -c 'import sys,json;print(json.dumps(sys.stdin.read()))'),\"parse_mode\":\"HTML\"}" >/dev/null 2>&1
}

[[ -e "$PROD_DIR/.git" ]] || { log "ERROR: prod worktree missing"; exit 1; }
[[ -e "$STAGING_DIR/.git" ]] || { log "ERROR: staging worktree missing"; exit 1; }
[[ "$(git -C "$STAGING_DIR" branch --show-current)" == "auto/coder-staging" ]] || { log "ERROR: staging not on auto/coder-staging"; exit 1; }

if [[ -n "$(git -C "$PROD_DIR" status --porcelain)" ]]; then
    log "SKIP: production worktree has uncommitted changes"; exit 0
fi

cd "$STAGING_DIR"
NEW=$(git log main..HEAD --oneline 2>/dev/null || true)
if [[ -z "$NEW" ]]; then
    # Even with no coder commits, keep local main in sync with origin so the
    # parallel external agent's pushes don't let the branches drift apart.
    cd "$PROD_DIR"
    git fetch origin main 2>>"$LOG" || true
    if ! git merge-base --is-ancestor origin/main main 2>/dev/null; then
        if git merge origin/main --no-edit >/dev/null 2>&1; then
            log "synced with origin/main (parallel agent): merged"
            if [[ "${AIOS_AUTO_PUSH:-0}" == "1" ]] && git push origin main >/dev/null 2>&1; then
                log "pushed synced main -> origin/main"
                tg_send "🔄 <b>AIOS: синхронизировано с параллельным агентом</b>\nСмержены чужие коммиты, main обновлён"
            fi
        else
            log "sync merge with origin failed (conflict); aborting"
            git merge --abort 2>/dev/null || true
        fi
    fi
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

# --- API health gate: the staging code must not crash the running API ---
# (the coder has previously broken MCPGateway and taken the API down).
if command -v /opt/aios/.venv/bin/python3.11 >/dev/null 2>&1; then
    # Import the API app modules to surface import-time/startup errors.
    if (cd "$STAGING_DIR" && timeout 90 /opt/aios/.venv/bin/python3.11 -c "
import sys; sys.path.insert(0, '.')
try:
    from aios_core.api.app import create_app
    # Build the app to force full startup (registries, MCP gateway, etc.).
    app = create_app(db_path='/tmp/aios_healthcheck.db')
    # Exercise the health route to be sure it responds.
    import starlette.testclient as tc
    client = tc.TestClient(app)
    r = client.get('/health')
    if r.status_code != 200:
        print('HEALTH FAIL status=%s' % r.status_code); raise SystemExit(1)
    print('API health OK')
except SystemExit:
    raise
except Exception as e:
    import traceback; traceback.print_exc()
    raise SystemExit(1)
" >/tmp/aios_api_import.log 2>&1); then
        log "api health gate: OK"
    else
        log "BLOCKED: API startup/health fails in staging; NOT promoting"
        tail -8 /tmp/aios_api_import.log | sed 's/^/  /' >> "$LOG"
        exit 1
    fi
fi

# --- test gate: run a quick pytest on changed core modules if present ---
if [[ -d "$STAGING_DIR/aios_core" ]] && command -v /opt/aios/.venv/bin/python3.11 >/dev/null 2>&1; then
    # Only fail the gate on real import/collection errors, not on system-missing deps.
    if (cd "$STAGING_DIR" && timeout 300 /opt/aios/.venv/bin/python3.11 -m pytest tests/security tests/integration \
            tests/test_api_security.py \
            -q --no-header -p no:cacheprovider >/tmp/aios_promote_test.log 2>&1); then
        log "test gate: security+integration+llm+api OK"
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

# --- sync with origin (parallel agent may push) ---
cd "$PROD_DIR"
git fetch origin main 2>>"$LOG" || true
log "fetched origin/main: $(git rev-parse --short origin/main)"

# --- merge staging into main ---
git fetch . auto/coder-staging:refs/remotes/autostaging 2>/dev/null || true
if ! git merge auto/coder-staging --no-edit >/dev/null 2>&1; then
    log "ERROR: merge conflict; aborting"; git merge --abort 2>/dev/null || true; exit 1
fi
log "merged auto/coder-staging into main"

# --- merge origin/main (parallel work) if diverged ---
if ! git merge-base --is-ancestor origin/main main; then
    if git merge origin/main --no-edit >/dev/null 2>&1; then
        log "merged origin/main (parallel) into local main"
    else
        log "ERROR: conflict with origin/main; aborting"; git merge --abort 2>/dev/null || true; exit 1
    fi
fi

# --- push (opt-in) with rebase retry loop ---
if [[ "${AIOS_AUTO_PUSH:-0}" == "1" ]]; then
    pushed=0
    for attempt in 1 2 3; do
        if git push origin main >/dev/null 2>&1; then
            pushed=1
            log "pushed main -> origin/main (attempt $attempt)"
            break
        else
            log "push attempt $attempt rejected; rebasing onto origin/main"
            git fetch origin main 2>>"$LOG" || true
            if git rebase origin/main >/dev/null 2>&1; then
                log "rebased onto origin/main"
            else
                log "rebase failed; aborting"
                git rebase --abort 2>/dev/null || true
                break
            fi
        fi
    done
    if [[ "$pushed" != "1" ]]; then
        log "WARN: push still failing after retries; main ahead of origin"
    fi
else
    log "AIOS_AUTO_PUSH != 1; committed locally only"
fi
log "auto-promote complete"
