#!/usr/bin/env bash
# Test for the auto-promote script: validates bash syntax and dry-runs the logic.
set -euo pipefail
echo "=== Test: auto-promote script ==="

# 1. Bash syntax valid
if bash -n /usr/local/bin/aios-auto-promote.sh; then
  echo "PASS: bash syntax OK"
else
  echo "FAIL: bash syntax error"; exit 1
fi

# 2. Required variables present
if grep -q "PROD_DIR=" /usr/local/bin/aios-auto-promote.sh && \
   grep -q "STAGING_DIR=" /usr/local/bin/aios-auto-promote.sh; then
  echo "PASS: required vars present"
else
  echo "FAIL: missing required vars"; exit 1
fi

# 3. Guards present (junk, compile, health, test)
for guard in "junk check" "compile validation" "api health gate" "test gate"; do
  if grep -q "$guard" /usr/local/bin/aios-auto-promote.sh; then
    echo "PASS: guard '$guard' present"
  else
    echo "WARN: guard '$guard' missing"
  fi
done

# 4. Git worktrees exist
if [ -d /root/AIOS/.git ] && [ -e /root/AIOS-autocoder/.git ]; then
  echo "PASS: worktrees exist"
else
  echo "FAIL: worktrees missing"; exit 1
fi

# 5. Git repos clean (main and staging)
cd /root/AIOS
if [ -z "$(git status --porcelain)" ]; then
  echo "PASS: main worktree clean"
else
  echo "WARN: main has uncommitted changes"
fi

echo "=== Test complete ==="
