from __future__ import annotations

from pathlib import Path

from scripts import generate_agents_status as MODULE


def _session(
    root: Path,
    session_id: str,
    *,
    status: str = "ACTIVE",
    updated: str = "2026-08-25T10:00:00Z",
    current: str = "Run tests",
) -> None:
    (root / "coordination" / "sessions").mkdir(parents=True, exist_ok=True)
    (root / "coordination" / "sessions" / f"{session_id}.md").write_text(
        f'''---
session_id: "{session_id}"
status: "{status}"
agent: "Test Agent"
started_utc: "2026-08-25T09:00:00Z"
updated_utc: "{updated}"
---

## Цель

Test dashboard generation.

## Текущий шаг (виден другим агентам)

- Текущий шаг: {current}

## Изменённые файлы

- `skills/arena/example/SKILL.md` — lesson.

## Handoff

- Следующий конкретный шаг: Finish the task.
''',
        encoding="utf-8",
    )


def _claim(root: Path, session_id: str, status: str = "ACTIVE") -> None:
    claims = root / "coordination" / "claims"
    claims.mkdir(parents=True, exist_ok=True)
    (claims / f"scope--{session_id}.md").write_text(
        f"""# Claim: scope
- Session: `{session_id}`
- Status: `{status}`
- Goal: Test claim parsing.
""",
        encoding="utf-8",
    )


def test_read_sessions_and_render_active_and_recent(tmp_path: Path) -> None:
    _session(tmp_path, "active", current="Implement parser")
    _session(
        tmp_path,
        "done",
        status="DONE",
        updated="2026-08-25T11:00:00Z",
        current="DONE — tests pass",
    )
    _claim(tmp_path, "active")

    sessions = MODULE.read_sessions(tmp_path / "coordination" / "sessions")
    dashboard = MODULE.render_dashboard(
        sessions, MODULE.read_claims(tmp_path / "coordination" / "claims")
    )

    assert [session.session_id for session in sessions] == ["done", "active"]
    assert "| Test Agent | Test dashboard generation. | Implement parser | ACTIVE |" in dashboard
    assert "DONE — tests pass" in dashboard
    assert "skills/arena/example/SKILL.md" in dashboard
    assert "Нет активных блокеров" in dashboard


def test_render_reports_stale_and_finished_claims(tmp_path: Path) -> None:
    _session(tmp_path, "done", status="DONE")
    _claim(tmp_path, "done")
    _claim(tmp_path, "old", status="DONE")

    dashboard = MODULE.render_dashboard(
        MODULE.read_sessions(tmp_path / "coordination" / "sessions"),
        MODULE.read_claims(tmp_path / "coordination" / "claims"),
    )

    assert "Stale ACTIVE claim `scope--done.md`: session is `DONE`" in dashboard
    assert "Finished claim `scope--old.md` remains" in dashboard


def test_atomic_write_and_check_mode(tmp_path: Path, monkeypatch) -> None:
    _session(tmp_path, "active")
    _claim(tmp_path, "active")
    output = tmp_path / "coordination" / "AGENTS_STATUS.md"
    rendered = MODULE.render_dashboard(
        MODULE.read_sessions(tmp_path / "coordination" / "sessions"),
        MODULE.read_claims(tmp_path / "coordination" / "claims"),
    )
    MODULE.atomic_write(output, rendered)

    assert output.read_text(encoding="utf-8") == rendered
    assert not list(output.parent.glob(".AGENTS_STATUS.md.*"))

    monkeypatch.setattr("sys.argv", ["generate_agents_status.py", "--repo", str(tmp_path), "--check"])
    assert MODULE.main() == 0
    output.write_text("stale\n", encoding="utf-8")
    assert MODULE.main() == 1
