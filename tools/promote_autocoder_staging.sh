#!/usr/bin/env bash
# Review gate for auto-coder staging changes. It never merges automatically.
set -euo pipefail

PROD_DIR="${AIOS_PROD_DIR:-/root/AIOS}"
STAGING_DIR="${AIOS_STAGING_DIR:-/root/AIOS-autocoder}"

[[ -e "$PROD_DIR/.git" ]] || { echo "Production worktree not found: $PROD_DIR" >&2; exit 1; }
[[ -e "$STAGING_DIR/.git" ]] || { echo "Staging worktree not found: $STAGING_DIR" >&2; exit 1; }

branch=$(git -C "$STAGING_DIR" branch --show-current)
[[ "$branch" == "auto/coder-staging" ]] || { echo "Unexpected staging branch: $branch" >&2; exit 1; }

echo "== Staging branch =="
git -C "$STAGING_DIR" status --short -b
echo
echo "== Changes versus production main =="
git -C "$STAGING_DIR" diff --stat main...HEAD

echo
echo "== Syntax validation =="
python3 -m compileall -q "$STAGING_DIR/aios_core" "$STAGING_DIR/run_coder_orchestrator.py"

echo
echo "Review passed. No merge or push was performed."
echo "After human review, merge explicitly from production worktree."
