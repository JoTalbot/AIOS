import io
import json

import pytest

from aios_core.openhands.ci_provenance import CIProvenanceCollector
from aios_core.openhands.errors import OpenHandsAPIError


class Response(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def test_collector_binds_run_and_job_to_exact_commit():
    commit = "a" * 40
    run_id = 101
    job_id = 202
    payloads = {
        f"/actions/runs?head_sha={commit}&per_page=100": {
            "workflow_runs": [
                {"id": run_id, "name": "AIOS Core Gate", "workflow_id": 1, "head_sha": commit, "status": "completed", "conclusion": "success"},
                {"id": 102, "name": "OpenHands Audit Integrity", "workflow_id": 2, "head_sha": commit, "status": "completed", "conclusion": "success"},
            ]
        },
        f"/actions/runs/{run_id}/jobs?per_page=100": {"jobs": [{"id": job_id, "name": "Core compile and targeted tests", "status": "completed", "conclusion": "success"}]},
        "/actions/runs/102/jobs?per_page=100": {"jobs": [{"id": 303, "name": "OpenHands audit chain integrity", "status": "completed", "conclusion": "success"}]},
    }

    def opener(request):
        path = request.full_url.split("/repos/JoTalbot/AIOS", 1)[1]
        return Response(json.dumps(payloads[path]).encode())

    result = CIProvenanceCollector("JoTalbot/AIOS", "token", api_opener=opener, sleep=lambda _: None).collect(commit, poll_interval=0)
    assert result.commit_sha == commit
    assert result.run_id == run_id
    assert result.job_id == job_id
    assert result.required_workflows == ("AIOS Core Gate", "OpenHands Audit Integrity")
    assert result.as_evidence()["ci_required_workflows_success"] is True


def test_failed_required_workflow_blocks():
    commit = "a" * 40

    def opener(request):
        path = request.full_url.split("/repos/JoTalbot/AIOS", 1)[1]
        if path.startswith("/actions/runs?"):
            return Response(json.dumps({"workflow_runs": [{"id": 10, "name": "AIOS Core Gate", "workflow_id": 1, "head_sha": commit, "status": "completed", "conclusion": "failure"}]}).encode())
        raise AssertionError(path)

    with pytest.raises(OpenHandsAPIError, match="concluded 'failure'"):
        CIProvenanceCollector("JoTalbot/AIOS", "token", api_opener=opener, sleep=lambda _: None).collect(commit, workflow_names=("AIOS Core Gate",), timeout=1)


def test_stale_run_is_not_accepted():
    commit = "a" * 40

    def opener(request):
        path = request.full_url.split("/repos/JoTalbot/AIOS", 1)[1]
        if path.startswith("/actions/runs?"):
            return Response(json.dumps({"workflow_runs": [{"id": 10, "name": "AIOS Core Gate", "workflow_id": 1, "head_sha": "c" * 40, "status": "completed", "conclusion": "success"}]}).encode())
        raise AssertionError(path)

    with pytest.raises(OpenHandsAPIError, match="timeout waiting"):
        CIProvenanceCollector("JoTalbot/AIOS", "token", api_opener=opener, sleep=lambda _: None).collect(commit, workflow_names=("AIOS Core Gate",), timeout=0)
