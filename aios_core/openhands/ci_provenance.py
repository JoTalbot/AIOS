"""GitHub Actions provenance collection for fail-closed OpenHands evidence."""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Callable, Sequence

from .errors import OpenHandsAPIError


@dataclass(frozen=True)
class CIProvenance:
    workflow_name: str
    workflow_id: int
    run_id: int
    job_id: int
    commit_sha: str
    conclusion: str
    job_name: str
    required_workflows: tuple[str, ...]

    def as_evidence(self) -> dict[str, object]:
        return {
            "ci_workflow_name": self.workflow_name,
            "ci_workflow_id": self.workflow_id,
            "ci_run_id": self.run_id,
            "ci_job_id": self.job_id,
            "ci_commit_sha": self.commit_sha,
            "ci_conclusion": self.conclusion,
            "ci_job_name": self.job_name,
            "ci_required_workflows": self.required_workflows,
            "ci_required_workflows_success": True,
        }


class CIProvenanceCollector:
    """Find successful GitHub Actions runs/jobs bound to exactly one commit."""

    def __init__(self, repo_slug: str, token: str, *, api_opener: object = urllib.request.urlopen, sleep: Callable[[float], None] = time.sleep) -> None:
        self.repo_slug = repo_slug
        self.token = token
        self.api_opener = api_opener
        self.sleep = sleep

    def _get(self, path: str) -> dict:
        if not self.repo_slug or not self.token:
            raise OpenHandsAPIError("CI provenance требует repo_slug и token")
        request = urllib.request.Request(
            f"https://api.github.com/repos/{self.repo_slug}{path}",
            headers={"Authorization": f"Bearer {self.token}", "Accept": "application/vnd.github+json"},
        )
        try:
            with self.api_opener(request) as response:
                return json.loads(response.read().decode())
        except urllib.error.HTTPError as exc:
            raise OpenHandsAPIError(f"GitHub Actions API HTTP {exc.code}: {exc.read().decode(errors='replace')[:300]}", status_code=exc.code) from exc

    def collect(self, commit_sha: str, *, workflow_names: Sequence[str] = ("AIOS Core Gate", "OpenHands Audit Integrity"), timeout: float = 600.0, poll_interval: float = 5.0) -> CIProvenance:
        required = tuple(dict.fromkeys(workflow_names))
        if not required:
            raise ValueError("workflow_names must not be empty")
        deadline = time.monotonic() + timeout
        while True:
            runs = self._get(f"/actions/runs?head_sha={commit_sha}&per_page=100").get("workflow_runs", [])
            candidates = [r for r in runs if r.get("name") in required and r.get("head_sha") == commit_sha]
            completed: dict[str, tuple[dict, dict]] = {}
            pending = False
            for workflow_name in required:
                matching = [r for r in candidates if r.get("name") == workflow_name]
                if not matching:
                    pending = True
                    continue
                run = max(matching, key=lambda r: r.get("id", 0))
                if run.get("status") != "completed":
                    pending = True
                    continue
                if run.get("conclusion") != "success":
                    raise OpenHandsAPIError(f"CI workflow {workflow_name} for {commit_sha[:12]} concluded {run.get('conclusion')!r}")
                jobs = self._get(f"/actions/runs/{run['id']}/jobs?per_page=100").get("jobs", [])
                successful = [j for j in jobs if j.get("status") == "completed" and j.get("conclusion") == "success"]
                if not successful:
                    raise OpenHandsAPIError(f"CI workflow {workflow_name} has no successful job")
                completed[workflow_name] = (run, successful[0])
            if len(completed) == len(required) and not pending:
                workflow_name = required[0]
                run, job = completed[workflow_name]
                return CIProvenance(
                    workflow_name=workflow_name,
                    workflow_id=int(run.get("workflow_id", 0)),
                    run_id=int(run["id"]),
                    job_id=int(job["id"]),
                    commit_sha=commit_sha,
                    conclusion="success",
                    job_name=str(job.get("name", "")),
                    required_workflows=required,
                )
            if time.monotonic() >= deadline:
                missing = [name for name in required if name not in completed]
                raise OpenHandsAPIError(f"timeout waiting for CI provenance for {commit_sha[:12]}: {missing}")
            self.sleep(poll_interval)
