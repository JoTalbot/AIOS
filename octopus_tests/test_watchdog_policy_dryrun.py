import json
import subprocess
import sys


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
