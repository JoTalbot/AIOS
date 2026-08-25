"""Тесты F6: вердикт из событий + ContourService (входная точка)."""

import pytest

from aios_core.openhands import ContourService, ContourStore, Gate, OHOrchestrator, TaskExtras, parse_review_verdict
from aios_core.openhands.audit import OHAuditLogger
from aios_core.openhands.models import ReviewDecision
from aios_core.orchestrator import TaskStatus
from tests.test_openhands_runner import FakeClient


@pytest.fixture
def audit(tmp_path):
    from aios_core.audit_logger import AuditLogger

    return OHAuditLogger(AuditLogger(file_path=str(tmp_path / "audit.jsonl")))


class VerdictClient(FakeClient):
    """Fake-клиент с задаваемым текстом событий."""

    def __init__(self, *args, event_texts: list[str] | None = None, **kw):
        super().__init__(*args, **kw)
        self.event_texts = event_texts or []

    def events_search(self, conversation_id, *, limit=100):
        return {"events": [{"message": t} for t in self.event_texts]}


class TestParseVerdict:
    def test_approved_token(self):
        payload = {"events": [{"message": "Проверил. APPROVED"}]}
        assert parse_review_verdict(payload) == ReviewDecision.APPROVED

    def test_changes_requested_token(self):
        payload = {"events": [{"message": "Есть замечания. CHANGES_REQUESTED: 2"}]}
        assert parse_review_verdict(payload) == ReviewDecision.CHANGES_REQUESTED

    def test_last_event_wins_and_changes_conservative(self):
        payload = {"events": [{"message": "APPROVED"}, {"message": "CHANGES_REQUESTED"}]}
        assert parse_review_verdict(payload) == ReviewDecision.CHANGES_REQUESTED

    def test_nested_structures(self):
        payload = {"events": [{"args": {"content": ["ok", "APPROVED"]}}]}
        assert parse_review_verdict(payload) == ReviewDecision.APPROVED

    def test_no_token_returns_none(self):
        assert parse_review_verdict({"events": [{"message": "привет"}]}) is None
        assert parse_review_verdict({}) is None


class TestRunnerVerdict:
    def test_changes_requested_blocks_and_retries(self, audit):
        client = VerdictClient(event_texts=["CHANGES_REQUESTED: нужны правки"])
        orch = OHOrchestrator(client=client, github=None, audit=audit)
        extras = TaskExtras(task_id="v-1", max_retries=1)
        result = orch.run("v-1", "Фича", "Описание", extras)
        # Reviewer отклоняет каждый раз: blocked → retry → blocked → cancelled.
        assert result.status == TaskStatus.CANCELLED
        assert result.report is not None
        decisions = audit.backend.query(event_type="openhands.decision")
        assert any(d.get("decision") == ReviewDecision.CHANGES_REQUESTED for d in decisions)


class TestAsyncRun:
    def _drain(self, service, task_id, timeout_s=10.0):
        import time

        deadline = time.monotonic() + timeout_s
        while service.is_running(task_id) and time.monotonic() < deadline:
            time.sleep(0.05)
        assert not service.is_running(task_id)

    def test_async_run_started_and_completes(self, audit):
        client = VerdictClient(event_texts=["APPROVED"])
        service = ContourService(client=client, github=None, audit=audit)
        task_id = service.submit("Сделать Z", "Описание Z")
        assert service.run_task_async(task_id) == "started"
        self._drain(service, task_id)
        status = service.status(task_id)
        assert status["contour_status"] == TaskStatus.COMPLETED
        assert status["running"] is False

    def test_async_duplicate_raises_409_semantics(self, audit):
        import threading

        started = threading.Event()
        release = threading.Event()
        client = VerdictClient(event_texts=["APPROVED"])

        def blocking_wait(cid, **kw):
            started.set()
            release.wait(10)
            return "idle"

        client.wait_execution = blocking_wait
        service = ContourService(client=client, github=None, audit=audit)
        task_id = service.submit("Фича", "Описание")
        assert service.run_task_async(task_id) == "started"
        assert started.wait(10)
        assert service.is_running(task_id)
        assert service.status(task_id)["running"] is True
        with pytest.raises(RuntimeError, match="уже выполняется"):
            service.run_task_async(task_id)
        release.set()
        self._drain(service, task_id)

    def test_async_unknown_task_raises(self, audit):
        service = ContourService(client=VerdictClient(), github=None, audit=audit)
        with pytest.raises(KeyError):
            service.run_task_async("nope")

    def test_approved_token_completes(self, audit):
        client = VerdictClient(event_texts=["Всё чисто. APPROVED"])
        orch = OHOrchestrator(client=client, github=None, audit=audit)
        result = orch.run("v-2", "Фича", "Описание")
        assert result.status == TaskStatus.COMPLETED

    def test_no_token_fallback_approved_and_audited(self, audit):
        client = VerdictClient(event_texts=["просто текст без маркера"])
        orch = OHOrchestrator(client=client, github=None, audit=audit)
        result = orch.run("v-3", "Фича", "Описание")
        assert result.status == TaskStatus.COMPLETED
        fallbacks = audit.backend.query(event_type="openhands.verdict_fallback")
        assert fallbacks

    def test_events_error_fallback(self, audit):
        client = VerdictClient()

        def boom(conversation_id, *, limit=100):
            raise RuntimeError("events api down")

        client.events_search = boom
        orch = OHOrchestrator(client=client, github=None, audit=audit)
        result = orch.run("v-4", "Фича", "Описание")
        assert result.status == TaskStatus.COMPLETED
        fallbacks = audit.backend.query(event_type="openhands.verdict_fallback")
        assert any("events api down" in f.get("reason", "") for f in fallbacks)


class TestContourService:
    def test_submit_run_status(self, audit):
        client = VerdictClient(event_texts=["APPROVED"])
        service = ContourService(client=client, github=None, audit=audit)
        task_id = service.submit("Сделать Y", "Описание Y")
        result = service.run_task(task_id)
        assert result.status == TaskStatus.COMPLETED
        status = service.status(task_id)
        assert status["canonical_status"] == TaskStatus.COMPLETED
        assert status["contour_status"] == TaskStatus.COMPLETED
        assert set(status["passed_gates"]) == {"tests", "review"}

    def test_cancelled_maps_to_canonical(self, audit):
        client = VerdictClient()

        def boom(cid, **kw):
            raise RuntimeError("boom")

        client.wait_execution = boom
        service = ContourService(client=client, github=None, audit=audit)
        task_id = service.submit("Фича", "Описание", max_retries=1)
        result = service.run_task(task_id)
        assert result.status == TaskStatus.CANCELLED
        status = service.status(task_id)
        assert status["canonical_status"] == TaskStatus.CANCELLED
        assert status["retry_count"] == 1

    def test_submit_with_gates_and_branch(self, audit):
        client = VerdictClient(event_texts=["APPROVED"])
        service = ContourService(client=client, github=None, audit=audit)
        task_id = service.submit(
            "Секьюрная фича",
            "Описание",
            required_gates=frozenset({Gate.TESTS, Gate.REVIEW, Gate.SECURITY_REVIEW}),
            branch="agent/custom",
        )
        result = service.run_task(task_id)
        assert result.status == TaskStatus.COMPLETED
        titles = [t for t, _ in client.started]
        assert f"aios-security-{task_id}" in titles
        # Разговоры идут на указанной ветке.
        _, prompt = client.started[0]
        assert "agent/custom" in prompt

    def test_status_unknown_task_raises(self, tmp_path, audit):
        store = ContourStore(state_dir=tmp_path)
        service = ContourService(client=VerdictClient(), github=None, audit=audit, store=store)
        with pytest.raises(KeyError):
            service.status("nope")
