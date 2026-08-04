"""Scheduled Android job manifest/dry-run tests."""
from __future__ import annotations


def test_jobs_snapshot_and_dry_run(tmp_path):
    from aios_core.phone_jobs import PhoneJobs

    # Create declared scripts so dry-run never executes them.
    from aios_core.phone_jobs import JOBS
    for _, _, script in JOBS:
        path = tmp_path / script
        path.write_text("x = 1\n", encoding="utf-8")
    report = PhoneJobs(tmp_path, service_probe=lambda _: True).snapshot()
    assert report["status"] == "ok"
    assert report["active"] == report["total"]
    dry = PhoneJobs(tmp_path, service_probe=lambda _: True).dry_run()
    assert dry["status"] == "ok"
