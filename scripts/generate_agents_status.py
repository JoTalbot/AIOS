#!/usr/bin/env python3
"""Generate the central AI agent status dashboard from coordination records."""

from __future__ import annotations

import argparse
import os
import re
import tempfile
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

ACTIVE_STATUSES = {"ACTIVE", "PAUSED", "BLOCKED"}
SESSION_GLOB = "*.md"
FIELD_RE = re.compile(r'^([a-z_]+):\s*["\']?(.*?)["\']?\s*$')
BULLET_RE = re.compile(r"^-\s*([^:]+):\s*(.*)$")


@dataclass(frozen=True)
class Session:
    """Normalized fields needed to render one session in the dashboard."""

    session_id: str
    status: str
    agent: str
    updated_utc: str
    goal: str
    current_step: str
    next_step: str
    skill: str


@dataclass(frozen=True)
class Claim:
    """Normalized fields needed to detect claim/session inconsistencies."""

    path: Path
    session_id: str
    status: str
    goal: str


def _frontmatter(text: str) -> dict[str, str]:
    lines = text.splitlines()
    try:
        start = lines.index("---")
        end = lines.index("---", start + 1)
    except ValueError:
        return {}

    fields: dict[str, str] = {}
    for line in lines[start + 1 : end]:
        match = FIELD_RE.match(line.strip())
        if match:
            fields[match.group(1)] = match.group(2)
    return fields


def _section(text: str, heading: str) -> str:
    marker = f"## {heading}"
    if marker not in text:
        return ""
    body = text.split(marker, 1)[1]
    return body.split("\n## ", 1)[0].strip()


def _first_content_line(section: str) -> str:
    for line in section.splitlines():
        value = line.strip().lstrip("- ")
        if value:
            return value
    return "—"


def _bullet_value(section: str, label: str) -> str:
    for line in section.splitlines():
        match = BULLET_RE.match(line.strip())
        if match and match.group(1).strip() == label:
            return match.group(2).strip() or "—"
    return "—"


def _skill_value(text: str) -> str:
    changed = _section(text, "Изменённые файлы")
    paths = re.findall(r"`(skills/[^`]+/SKILL\.md)`", changed)
    return ", ".join(paths) if paths else "—"


def read_sessions(sessions_dir: Path) -> list[Session]:
    """Read valid session journals, newest first."""
    sessions: list[Session] = []
    for path in sessions_dir.glob(SESSION_GLOB):
        if path.name == "README.md":
            continue
        text = path.read_text(encoding="utf-8")
        fields = _frontmatter(text)
        if not fields.get("session_id"):
            continue
        current = _section(text, "Текущий шаг (виден другим агентам)")
        handoff = _section(text, "Handoff")
        sessions.append(
            Session(
                session_id=fields["session_id"],
                status=fields.get("status", "UNKNOWN").upper(),
                agent=fields.get("agent", "unknown"),
                updated_utc=fields.get("updated_utc", fields.get("started_utc", "")),
                goal=_first_content_line(_section(text, "Цель")),
                current_step=_bullet_value(current, "Текущий шаг"),
                next_step=_bullet_value(handoff, "Следующий конкретный шаг"),
                skill=_skill_value(text),
            )
        )
    return sorted(sessions, key=lambda item: (item.updated_utc, item.session_id), reverse=True)


def read_claims(claims_dir: Path) -> list[Claim]:
    """Read advisory claims while ignoring the directory README."""
    claims: list[Claim] = []
    for path in claims_dir.glob("*.md"):
        if path.name == "README.md":
            continue
        values: dict[str, str] = {}
        for line in path.read_text(encoding="utf-8").splitlines():
            match = BULLET_RE.match(line.strip())
            if match:
                values[match.group(1).strip()] = match.group(2).strip().strip("`")
        claims.append(
            Claim(
                path=path,
                session_id=values.get("Session", "unknown"),
                status=values.get("Status", "UNKNOWN").upper(),
                goal=values.get("Goal", "—"),
            )
        )
    return sorted(claims, key=lambda item: item.path.name)


def _cell(value: str) -> str:
    return " ".join(value.replace("|", "\\|").split())


def _table(rows: Iterable[Iterable[str]], empty_columns: int) -> list[str]:
    rendered = ["| " + " | ".join(_cell(value) for value in row) + " |" for row in rows]
    return rendered or ["| " + " | ".join("—" for _ in range(empty_columns)) + " |"]


def render_dashboard(sessions: list[Session], claims: list[Claim], recent_limit: int = 10) -> str:
    """Render a deterministic Markdown dashboard."""
    active = [session for session in sessions if session.status in ACTIVE_STATUSES]
    recent = [session for session in sessions if session.status not in ACTIVE_STATUSES][:recent_limit]
    by_id = {session.session_id: session for session in sessions}

    inconsistencies: list[str] = []
    for claim in claims:
        session = by_id.get(claim.session_id)
        if claim.status == "ACTIVE" and session and session.status not in ACTIVE_STATUSES:
            inconsistencies.append(
                f"Stale ACTIVE claim `{claim.path.name}`: session is `{session.status}`."
            )
        elif claim.status != "ACTIVE":
            inconsistencies.append(
                f"Finished claim `{claim.path.name}` remains in `coordination/claims/` "
                f"with status `{claim.status}`."
            )
        elif not session:
            inconsistencies.append(
                f"Claim `{claim.path.name}` references missing session `{claim.session_id}`."
            )

    lines = [
        "# AIOS Agents Status Dashboard",
        "",
        "> Generated by `python scripts/generate_agents_status.py`. Do not edit table rows manually.",
        "",
        "## Активные агенты",
        "",
        "| Агент | Задача | Текущий шаг | Статус | Следующий шаг |",
        "|---|---|---|---|---|",
        *_table(
            (
                (item.agent, item.goal, item.current_step, item.status, item.next_step)
                for item in active
            ),
            5,
        ),
        "",
        "## Последние изменения",
        "",
        "| Обновлено UTC | Агент | Результат | Skill получен |",
        "|---|---|---|---|",
        *_table(
            (
                (item.updated_utc or "—", item.agent, item.current_step, item.skill)
                for item in recent
            ),
            4,
        ),
        "",
        "## Блокеры и несогласованности",
        "",
    ]
    lines.extend(f"- {message}" for message in inconsistencies)
    if not inconsistencies:
        lines.append("Нет активных блокеров или несогласованностей coordination metadata.")
    lines.extend(
        [
            "",
            "## Принцип",
            "",
            "Dashboard — производное представление. Источники истины: отдельные журналы",
            "`coordination/sessions/`, advisory claims в `coordination/claims/` и фактическое",
            "состояние Git. Обновление: `python scripts/generate_agents_status.py`; проверка",
            "дрейфа: `python scripts/generate_agents_status.py --check`.",
            "",
        ]
    )
    return "\n".join(lines)


def atomic_write(path: Path, content: str) -> None:
    """Replace *path* from a same-directory temporary file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=path.parent, prefix=f".{path.name}.", delete=False
        ) as handle:
            handle.write(content)
            temp_path = Path(handle.name)
        os.replace(temp_path, path)
    finally:
        if temp_path and temp_path.exists():
            temp_path.unlink()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--check", action="store_true", help="fail when the dashboard is stale")
    args = parser.parse_args()

    repo = args.repo.resolve()
    output = repo / "coordination" / "AGENTS_STATUS.md"
    rendered = render_dashboard(
        read_sessions(repo / "coordination" / "sessions"),
        read_claims(repo / "coordination" / "claims"),
    )
    if args.check:
        current = output.read_text(encoding="utf-8") if output.exists() else ""
        if current != rendered:
            print(f"STALE: {output}")
            return 1
        print(f"OK: {output}")
        return 0

    atomic_write(output, rendered)
    print(f"UPDATED: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
