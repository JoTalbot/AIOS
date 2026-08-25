"""Тесты F7: ContourStore — персистентность контурного состояния."""

import pytest

from aios_core.openhands import ContourService, ContourStore, Gate, TaskExtras
from aios_core.openhands.audit import OHAuditLogger
from aios_core.openhands.store import extras_from_dict, extras_to_dict, task_from_dict, task_to_dict
from aios_core.orchestrator import Task, TaskStatus
from tests.test_openhands_runner import FakeClient


@pytest.fixture
def audit(tmp_path):
    from aios_core.audit_logger import AuditLogger

    return OHAuditLogger(AuditLogger(file_path=str(tmp_path / "audit.jsonl")))


class TestExtrasRoundTrip:
    def test_defaults(self):
        extras = TaskExtras(task_id="t-1")
        restored = extras_from_dict(extras_to_dict(extras))
        assert restored.task_id == extras.task_id
        assert restored.required_gates == extras.required_gates
        assert restored.passed_gates == frozenset()
        assert restored.max_retries == 3

    def test_populated(self):
        extras = TaskExtras(
            task_id="t-2",
            branch="agent/x",
            workspace="ws-1",
            required_capabilities=("code",),
            dependencies=("t-0",),
            required_gates=frozenset({Gate.TESTS, Gate.REVIEW, Gate.QA}),
            passed_gates=frozenset({Gate.TESTS}),
            conversation_ids={"architect": "c-1"},
            retry_count=2,
            max_retries=5,
            artifacts=("report.md",),
            error="boom",
        )
        restored = extras_from_dict(extras_to_dict(extras))
        assert restored.branch == "agent/x"
        assert restored.required_capabilities == ("code",)
        assert restored.required_gates == extras.required_gates
        assert restored.passed_gates == frozenset({Gate.TESTS})
        assert restored.conversation_ids == {"architect": "c-1"}
        assert restored.retry_count == 2
        assert restored.artifacts == ("report.md",)
        assert restored.error == "boom"


class TestTaskRoundTrip:
    def test_minimal(self):
        task = Task(name="N", description="D", agent_id="oh-orchestrator")
        restored = task_from_dict(task_to_dict(task))
        assert restored.id == task.id
        assert restored.name == "N"
        assert restored.status == TaskStatus.PENDING

    def test_completed_status_and_error(self):
        task = Task(name="N", description="D")
        task.status = TaskStatus.CANCELLED
        task.error = "лимит"
        restored = task_from_dict(task_to_dict(task))
        assert restored.status == TaskStatus.CANCELLED
        assert restored.error == "лимит"

    def test_unknown_status_falls_back_to_pending(self):
        data = task_to_dict(Task(name="N", description="D"))
        data["status"] = "unmapped_oh_status"
        assert task_from_dict(data).status == TaskStatus.PENDING


class TestContourStore:
    def test_save_and_load(self, tmp_path):
        store = ContourStore(state_dir=tmp_path)
        task = Task(name="X", description="Y", agent_id="oh-orchestrator")
        extras = TaskExtras(task_id=task.id, branch="agent/b")
        store.save(task, extras, contour_status=TaskStatus.COMPLETED)
        loaded = store.load(task.id)
        assert loaded is not None
        task2, extras2, contour_status = loaded
        assert task2.name == "X"
        assert extras2.branch == "agent/b"
        assert contour_status == TaskStatus.COMPLETED

    def test_load_missing_returns_none(self, tmp_path):
        assert ContourStore(state_dir=tmp_path).load("nope") is None

    def test_corrupted_file_returns_empty(self, tmp_path):
        (tmp_path / "oh_contour_tasks.json").write_text("{not json")
        store = ContourStore(state_dir=tmp_path)
        assert store.list_ids() == []
        assert store.load("any") is None

    def test_overwrite_same_task(self, tmp_path):
        store = ContourStore(state_dir=tmp_path)
        task = Task(name="X", description="Y")
        extras = TaskExtras(task_id=task.id)
        store.save(task, extras)
        extras.retry_count = 2
        store.save(task, extras)
        assert len(store.list_ids()) == 1
        assert store.load(task.id)[1].retry_count == 2

    def test_atomic_write_no_tmp_leftovers(self, tmp_path):
        store = ContourStore(state_dir=tmp_path)
        task = Task(name="X", description="Y")
        store.save(task, TaskExtras(task_id=task.id))
        assert (tmp_path / "oh_contour_tasks.json").exists()
        assert list(tmp_path.glob("*.tmp")) == []

    def test_concurrent_saves_consistent(self, tmp_path):
        import threading

        store = ContourStore(state_dir=tmp_path)

        def save_one(i):
            task = Task(name=f"t{i}", description="d")
            store.save(task, TaskExtras(task_id=f"t-{i}"), contour_status="pending")

        threads = [threading.Thread(target=save_one, args=(i,)) for i in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert len(store.list_ids()) == 20
        assert list(tmp_path.glob("*.tmp")) == []


class TestServicePersistence:
    def test_submit_persists_and_restore_after_restart(self, tmp_path, audit):
        store = ContourStore(state_dir=tmp_path)
        service1 = ContourService(client=FakeClient(), github=None, audit=audit, store=store)
        task_id = service1.submit("Задача", "Описание")
        # «Рестарт»: новый сервис на том же store.
        service2 = ContourService(client=FakeClient(), github=None, audit=audit, store=store)
        status = service2.status(task_id)
        assert status["title"] == "Задача"
        assert status["contour_status"] == TaskStatus.PENDING

    def test_run_persists_completed_state(self, tmp_path, audit):
        store = ContourStore(state_dir=tmp_path)
        service1 = ContourService(client=FakeClient(), github=None, audit=audit, store=store)
        task_id = service1.submit("Фича", "Описание")
        result = service1.run_task(task_id)
        assert result.status == TaskStatus.COMPLETED
        service2 = ContourService(client=FakeClient(), github=None, audit=audit, store=store)
        status = service2.status(task_id)
        assert status["canonical_status"] == TaskStatus.COMPLETED
        assert status["contour_status"] == TaskStatus.COMPLETED
        assert set(status["passed_gates"]) == {"tests", "review"}

    def test_status_reads_store_lazily(self, tmp_path, audit):
        store = ContourStore(state_dir=tmp_path)
        service1 = ContourService(client=FakeClient(), github=None, audit=audit, store=store)
        task_id = service1.submit("Фича", "Описание")
        service1.run_task(task_id)
        # Свежий сервис, _tasks пуст — status идёт в store.
        service2 = ContourService(client=FakeClient(), github=None, audit=audit, store=store)
        assert service2.status(task_id)["contour_status"] == TaskStatus.COMPLETED

    def test_env_override_state_dir(self, tmp_path, monkeypatch):
        monkeypatch.delenv("OCTOPUS_ORCHESTRATOR_STATE_DIR", raising=False)
        monkeypatch.setenv("OH_CONTOUR_STATE_DIR", str(tmp_path))
        import aios_core.openhands.store as store_module

        monkeypatch.setattr(store_module, "_DEFAULT_DIR", tmp_path)
        store = ContourStore()
        task = Task(name="X", description="Y")
        store.save(task, TaskExtras(task_id=task.id))
        assert (tmp_path / "oh_contour_tasks.json").exists()
