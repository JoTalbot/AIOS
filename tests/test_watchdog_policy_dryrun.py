import json
import os
import subprocess
import sys

import pytest

DRY_RUN_SCRIPT = "scripts/octopus-watchdog-policy-dryrun.py"
pytestmark = pytest.mark.skipif(
    not os.path.exists(DRY_RUN_SCRIPT),
    reason="octopus-watchdog-policy-dryrun.py отсутствует на этом хосте",
)


def test_watchdog_policy_dryrun_json_reports_no_restarts():
    result = subprocess.run(
        [sys.executable, "scripts/octopus-watchdog-policy-dryrun.py", "--json"],
        check=True,
        text=True,
        capture_output=True,
    )
    payload = json.loads(result.stdout)
    assert payload["dry_run"] is True
    assert payload["restarts_executed"] == 0
    assert payload["node_count"] >= 1
    assert payload["error_count"] == 0


def test_watchdog_policy_dryrun_plain_mentions_no_restarts():
    result = subprocess.run(
        [sys.executable, "scripts/octopus-watchdog-policy-dryrun.py"],
        check=True,
        text=True,
        capture_output=True,
    )
    assert "restarts_executed=0" in result.stdout
    assert "error_count=0" in result.stdout
