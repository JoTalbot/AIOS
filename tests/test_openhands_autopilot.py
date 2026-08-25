"""Тесты автопилота контура: коллекторы очереди и подача в ContourService.

Без моков: реальные файловые сканеры по tmp-tree, реальный lifecycle
через FakeClient (см. ``tests/test_openhands_runner``), сеть не используется.
"""

import argparse

import pytest

from aios_core.openhands import ContourService, ContourStore
from aios_core.orchestrator import TaskStatus
from scripts.openhands_autopilot import (
    AutopilotResult,
    TaskDraft,
    collect_todo,
    main,
    parse_ruff_output,
    submit_queue,
)
from tests.test_openhands_runner import FakeClient


@pytest.fixture
def service(tmp_path):
    return ContourService(
        client=FakeClient(),
        github=None,
        store=ContourStore(state_dir=tmp_path / "state"),
    )


class TestCollectTodo:
    def test_groups_markers_by_file(self, tmp_path):
        (tmp_path / "a.py").write_text("# TODO: досыпать\nx = 1\n# FIXME: починить\n")
        drafts = collect_todo(tmp_path)
        assert [d.title for d in drafts] == ["TODO/FIXME: a.py"]
        assert "L1" in drafts[0].description and "L3" in drafts[0].description

    def test_skips_service_dirs(self, tmp_path):
        (tmp_path / ".git").mkdir()
        (tmp_path / ".git" / "x.py").write_text("# TODO: нет\n")
        assert collect_todo(tmp_path) == []

    def test_deterministic_order(self, tmp_path):
        for name in ("b.py", "a.py", "c.py"):
            (tmp_path / name).write_text("# FIXME: разберём\n")
        assert [d.title for d in collect_todo(tmp_path)] == [f"TODO/FIXME: {n}" for n in ("a.py", "b.py", "c.py")]


class TestParseRuff:
    def test_grouped_by_path(self):
        text = "aios_core/x.py:1:5: F401 unused\naios_core/x.py:2:1: E501 long\nscripts/y.py:9:3: W291 ws\n"
        grouped = parse_ruff_output(text)
        assert grouped["aios_core/x.py"] == ["F401 unused", "E501 long"]
        assert grouped["scripts/y.py"] == ["W291 ws"]

    def test_ignores_non_matching_lines(self):
        assert parse_ruff_output("all done?\n") == {}


class TestSubmitQueue:
    def test_dedups_against_existing_titles(self, service):
        service.submit("TODO/FIXME: a.py", "описание")
        drafts = [TaskDraft("todo", "TODO/FIXME: a.py", "описание"), TaskDraft("todo", "TODO/FIXME: b.py", "op")]
        res = submit_queue(service, drafts)
        assert res.skipped_duplicates == ["TODO/FIXME: a.py"]
        assert len(res.submitted) == 1

    def test_max_tasks_cap(self, service):
        drafts = [TaskDraft("todo", f"t-{i}", "op") for i in range(5)]
        res = submit_queue(service, drafts, max_tasks=2)
        assert len(res.submitted) == 2

    def test_run_lifecycle_with_fake_client(self, service):
        res = submit_queue(
            service,
            [TaskDraft("todo", "TODO/FIXME: a.py", "описание")],
        )
        (task_id,) = res.submitted
        run = service.run_task(task_id)
        res2 = AutopilotResult(submitted=[task_id])
        res2.executed[task_id] = str(run.status)
        assert res2.executed[task_id] == str(TaskStatus.COMPLETED)


class TestMain:
    def test_plan_prints_queue_and_exits_zero(self, tmp_path, capsys):
        (tmp_path / "x.py").write_text("# TODO: 1\n")
        assert main(["--plan", "--root", str(tmp_path)]) == 0
        out = capsys.readouterr().out
        assert "TODO/FIXME: x.py" in out


class TestBuildService:
    def test_service_factory_accepts_repo_and_branch(self, monkeypatch):
        from scripts import openhands_autopilot as ap

        fake = FakeClient()
        monkeypatch.setattr(ap, "OpenHandsClient", lambda: fake)
        args = argparse.Namespace(repository="owner/repo", base_branch="dev")
        svc = ap._build_service(args)
        assert svc.repository == "owner/repo" and svc.base_branch == "dev"
