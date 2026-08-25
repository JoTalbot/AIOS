"""Тесты оркестратора контура (F5): lifecycle, retry, gates, finalize.

Cloud-клиент — fake по Protocol (реальный runner-код, реальная state machine,
реальный audit, реальный git tmp-repo). Сеть не используется.
"""

import pytest

from aios_core.openhands import (
    Gate,
    GitHubHelper,
    OHOrchestrator,
    TaskExtras,
)
from aios_core.openhands.audit import OHAuditLogger
from aios_core.openhands.errors import OpenHandsAPIError
from aios_core.orchestrator import TaskStatus


class FakeClient:
    """Fake Cloud-клиента: запоминает вызовы, вердикт Reviewer задаётся снаружи."""

    def __init__(self, verdict: str = "approved", fail_on_role: str | None = None):
        self.started: list[tuple[str, str]] = []  # (title, prompt)
        self.executions: list[str] = []
        self.verdict = verdict
        self.fail_on_role = fail_on_role
        self._n = 0

    def start_conversation(self, prompt, *, repository=None, branch=None, title=None, run=True):
        self._n += 1
        self.started.append((title, prompt))
        return {"id": f"st-{self._n}", "app_conversation_id": f"c-{self._n}"}

    def wait_start_task(self, start_task_id, **kw):
        return {"id": start_task_id, "status": "READY", "app_conversation_id": f"c-{start_task_id}"}

    def wait_execution(self, conversation_id, **kw):
        self.executions.append(conversation_id)
        return "idle"

    def conversation_url(self, conversation_id):
        return f"https://app.all-hands.dev/conversations/{conversation_id}"


@pytest.fixture
def audit(tmp_path):
    from aios_core.audit_logger import AuditLogger

    return OHAuditLogger(AuditLogger(file_path=str(tmp_path / "audit.jsonl")))


class TestHappyPath:
    def test_full_mvp_flow_without_github(self, audit):
        client = FakeClient()
        orch = OHOrchestrator(client=client, github=None, audit=audit)
        result = orch.run("t-1", "Сделать X", "Описание X")
        assert result.status == TaskStatus.COMPLETED
        assert result.report is None
        # Architect, Coder, Tester, Reviewer — ровно 4 разговора MVP.
        roles = [t for t, _ in client.started]
        assert roles == ["aios-architect-t-1", "aios-coder-t-1", "aios-tester-t-1", "aios-reviewer-t-1"]
        gates = result.extras.passed_gates
        assert Gate.TESTS in gates and Gate.REVIEW in gates

    def test_optional_gates_extend_flow(self, audit):
        client = FakeClient()
        extras = TaskExtras(
            task_id="t-2",
            required_gates=frozenset({Gate.TESTS, Gate.REVIEW, Gate.SECURITY_REVIEW, Gate.QA}),
        )
        orch = OHOrchestrator(client=client, github=None, audit=audit)
        result = orch.run("t-2", "Секьюрная фича", "Описание", extras)
        assert result.status == TaskStatus.COMPLETED
        titles = [t for t, _ in client.started]
        assert "aios-security-t-2" in titles and "aios-qa-t-2" in titles


class TestRetry:
    def test_coder_failure_retries_then_completes(self, audit):
        client = FakeClient()
        calls = {"coder": 0}
        orig_wait = client.wait_execution

        def flaky(conversation_id, **kw):
            # Первый coder-разговор (c-2) падает один раз.
            if conversation_id == "c-2" and calls["coder"] == 0:
                calls["coder"] += 1
                raise OpenHandsAPIError("coder exploded")
            return orig_wait(conversation_id, **kw)

        client.wait_execution = flaky
        orch = OHOrchestrator(client=client, github=None, audit=audit)
        result = orch.run("t-3", "Фича", "Описание")
        assert result.status == TaskStatus.COMPLETED
        assert result.extras.retry_count == 1

    def test_retry_limit_exhausted_produces_report(self, audit):
        client = FakeClient()

        def always_fail(conversation_id, **kw):
            raise OpenHandsAPIError("boom")

        client.wait_execution = always_fail
        orch = OHOrchestrator(client=client, github=None, audit=audit)
        extras = TaskExtras(task_id="t-4", max_retries=3)
        result = orch.run("t-4", "Фича", "Описание", extras)
        assert result.status == TaskStatus.CANCELLED  # исчерпание лимита → только CANCELLED
        assert result.report is not None
        assert result.report.attempts == 4  # 1 + 3 retry
        assert "boom" in (result.report.last_error or "")


class TestFinalize:
    def test_denied_paths_block_completion(self, audit, tmp_path):
        repo = tmp_path / "repo"
        repo.mkdir()
        import subprocess

        subprocess.run(["git", "init", "-b", "main"], cwd=repo, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.email", "t@t"], cwd=repo, check=True)
        subprocess.run(["git", "config", "user.name", "t"], cwd=repo, check=True)
        (repo / "base.txt").write_text("base")
        subprocess.run(["git", "add", "."], cwd=repo, check=True)
        subprocess.run(["git", "commit", "-m", "init"], cwd=repo, check=True, capture_output=True)

        gh = GitHubHelper(repo, repo_slug="o/r", token="t")
        gh.create_branch("agent/oh-t5")
        # Coder «смошенничал»: изменил protected-файл.
        (repo / "run_telegram_bot.py").write_text("hacked = True\n")
        gh.commit_paths(["run_telegram_bot.py"], "hack")

        client = FakeClient()
        orch = OHOrchestrator(client=client, github=gh, audit=audit)
        extras = TaskExtras(task_id="t-5", branch="agent/oh-t5")
        result = orch.run("t-5", "Фича", "Описание", extras)
        # finalize падает → задача не COMPLETED, попытки исчерпаны → отчёт.
        assert result.status != TaskStatus.COMPLETED
        assert result.report is not None
        assert "run_telegram_bot.py" in result.report.files_changed

    def test_clean_diff_creates_pr(self, audit, tmp_path):
        repo = tmp_path / "repo2"
        repo.mkdir()
        import io
        import json
        import subprocess

        subprocess.run(["git", "init", "-b", "main"], cwd=repo, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.email", "t@t"], cwd=repo, check=True)
        subprocess.run(["git", "config", "user.name", "t"], cwd=repo, check=True)
        (repo / "base.txt").write_text("base")
        subprocess.run(["git", "add", "."], cwd=repo, check=True)
        subprocess.run(["git", "commit", "-m", "init"], cwd=repo, check=True, capture_output=True)

        # Локальный remote для push.
        remote = tmp_path / "remote.git"
        subprocess.run(["git", "init", "--bare", str(remote)], check=True, capture_output=True)
        subprocess.run(["git", "remote", "add", "origin", str(remote)], cwd=repo, check=True)

        class FakeResponse(io.BytesIO):
            def __enter__(self):
                return self

            def __exit__(self, *exc):
                return False

        def opener(request):
            return FakeResponse(json.dumps({"html_url": "https://x/pr/9"}).encode())

        gh = GitHubHelper(repo, repo_slug="o/r", token="t", api_opener=opener)
        gh.create_branch("agent/oh-t6")
        (repo / "feature.py").write_text("x = 1\n")
        gh.commit_paths(["feature.py"], "oh(t6): feature")

        client = FakeClient()
        orch = OHOrchestrator(client=client, github=gh, audit=audit)
        extras = TaskExtras(task_id="t-6", branch="agent/oh-t6")
        result = orch.run("t-6", "Фича", "Описание", extras)
        assert result.status == TaskStatus.COMPLETED
        assert "https://x/pr/9" in result.extras.artifacts


class TestAuditTrail:
    def test_transitions_logged(self, audit, tmp_path):
        client = FakeClient()
        orch = OHOrchestrator(client=client, github=None, audit=audit)
        orch.run("t-7", "Фича", "Описание")
        events = audit.backend.query(event_type="openhands.transition")
        chain = [(e["src"], e["dst"]) for e in events]
        assert chain[0] == ("pending", "planning")
        assert (str(TaskStatus.RUNNING), "testing") in chain
        assert ("qa", "completed") not in chain  # без QA-гейта
        assert chain[-1][1] == "completed"
