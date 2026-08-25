"""Автономный генератор задач OpenHands-контура по всему проекту.

Сканирует репозиторий коллекторами (`todo`: TODO/FIXME-маркеры, `ruff`:
lint-замечания), формирует упорядоченную очередь и подаёт её в
``ContourService``. По умолчанию работает в безопасном режиме ``--plan``
(печать очереди, без обращений к Cloud); исполнение — только с флагом
``--run`` и наличием ``OPENHANDS_API_KEY``.

Детальное описание lifecycle — ``docs/AIOS_AGENT_ARCHITECTURE.md`` и
``docs/TASK_LIFECYCLE.md``.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from aios_core.openhands import ContourService, Gate, OpenHandsClient

RUFF_SCOPE = ("aios_core", "octopus_core", "scripts")
MARKER_PREFIXES = ("TODO:", "TODO(", "FIXME:", "FIXME(")

# Токены, подвергаемые исключению при обходе корня.
_SKIP_DIRS = {".git", ".venv", "venv", "node_modules", "__pycache__", ".ruff_cache"}


@dataclass
class TaskDraft:
    """Черновик задачи очереди."""

    collector: str
    title: str
    description: str

    def as_dict(self) -> dict[str, str]:
        return {"collector": self.collector, "title": self.title, "description": self.description}


@dataclass
class AutopilotResult:
    """Сводка исполнения."""

    submitted: list[str] = field(default_factory=list)
    skipped_duplicates: list[str] = field(default_factory=list)
    executed: dict[str, str] = field(default_factory=dict)


def _iter_source_files(root: Path) -> list[Path]:
    """Все ``*.py``-файлы, кроме служебных каталогов; детерминированный порядок."""
    files = [
        p
        for p in root.rglob("*.py")
        if not any(part in _SKIP_DIRS for part in p.parts)
    ]
    return sorted(files, key=lambda p: p.relative_to(root).as_posix())


def collect_todo(root: Path, *, max_files: int = 50, max_lines: int = 5) -> list[TaskDraft]:
    """Сгруппировать маркеры TODO/FIXME по файлам — одна задача на файл."""
    drafts: list[TaskDraft] = []
    for path in _iter_source_files(root):
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        hits = [
            f"L{lineno}: {line.strip()}"
            for lineno, line in enumerate(text.splitlines(), 1)
            if any(prefix in line for prefix in MARKER_PREFIXES)
        ]
        if not hits:
            continue
        rel = path.relative_to(root).as_posix()
        sample = "\n".join(hits[:max_lines])
        drafts.append(
            TaskDraft(
                collector="todo",
                title=f"TODO/FIXME: {rel}",
                description=f"Устранить маркеры TODO/FIXME в `{rel}`:\n{sample}",
            )
        )
        if len(drafts) >= max_files:
            break
    return drafts


def parse_ruff_output(text: str) -> dict[str, list[str]]:
    """Разобрать output ruff ``path:l:c: CODE msg`` в {path: [сообщения]}."""
    grouped: dict[str, list[str]] = {}
    for line in text.splitlines():
        parts = line.split(":", 3)
        if len(parts) < 4:
            continue
        path, msg = parts[0], parts[3].strip()
        grouped.setdefault(path, []).append(msg)
    return grouped


def collect_ruff(
    root: Path,
    *,
    scope: tuple[str, ...] = RUFF_SCOPE,
    max_files: int = 50,
    max_msgs: int = 5,
) -> list[TaskDraft]:
    """Запустить ``ruff check`` (output-format=txt) и сгруппировать по файлам."""
    targets = [s for s in scope if (root / s).exists()]
    if not targets:
        return []
    binary = shutil.which("ruff")
    cmd = [binary] if binary else [sys.executable, "-m", "ruff"]
    try:
        proc = subprocess.run(
            [*cmd, "check", "--output-format=txt", "--no-fix", *targets],
            cwd=root,
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        return []
    grouped = parse_ruff_output(proc.stdout)
    drafts: list[TaskDraft] = []
    for rel in sorted(grouped):
        msgs = grouped[rel]
        sample = "\n".join(f"{rel}: {m}" for m in msgs[:max_msgs])
        drafts.append(
            TaskDraft(
                collector="ruff",
                title=f"Ruff-замечания: {rel}",
                description=f"Устранить замечания ruff в `{rel}`:\n{sample}",
            )
        )
        if len(drafts) >= max_files:
            break
    return drafts


def collect_queue(
    root: Path,
    *,
    collectors: tuple[str, ...] = ("ruff", "todo"),
    max_per_collector: int = 50,
) -> list[TaskDraft]:
    """Собрать очередь из выбранных коллекторов в фиксированном порядке."""
    queue: list[TaskDraft] = []
    for name in collectors:
        if name == "ruff":
            queue.extend(collect_ruff(root, max_files=max_per_collector))
        elif name == "todo":
            queue.extend(collect_todo(root, max_files=max_per_collector))
        else:
            raise ValueError(f"неизвестный коллектор: {name}")
    return queue


def submit_queue(
    service: ContourService,
    drafts: list[TaskDraft],
    *,
    gates: frozenset[Gate] | None = None,
    max_tasks: int | None = None,
) -> AutopilotResult:
    """Подать черновики в сервис, пропуская дубликаты по заголовку."""
    known = {entry.task.name for entry in service._tasks.values()}
    result = AutopilotResult()
    for draft in drafts:
        if max_tasks is not None and len(result.submitted) >= max_tasks:
            break
        if draft.title in known:
            result.skipped_duplicates.append(draft.title)
            continue
        task_id = service.submit(draft.title, draft.description, required_gates=gates)
        known.add(draft.title)
        result.submitted.append(task_id)
    return result


def _build_service(args: argparse.Namespace) -> ContourService:
    """Реальный Cloud-клиент; ошибка авторизации выводится по-человечески."""

    return ContourService(
        client=OpenHandsClient(),
        base_branch=args.base_branch,
        repository=args.repository or None,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".", help="корень репозитория")
    parser.add_argument("--plan", action="store_true", default=False, help="только печать очереди")
    parser.add_argument("--run", action="store_true", help="исполнить очередь через Cloud")
    parser.add_argument("--max-tasks", type=int, help="лимит подач")
    parser.add_argument("--collectors", default="ruff,todo", help="ruff,todo (порядок)")
    parser.add_argument("--repository", default="", help="owner/repo для Cloud-разговоров")
    parser.add_argument("--base-branch", default="main")
    args = parser.parse_args(argv)

    collectors = tuple(name.strip() for name in args.collectors.split(","))
    root = Path(args.root).resolve()
    queue = collect_queue(root, collectors=collectors)

    if not queue:
        print("🔎 Очередь пуста: замечаний нет.")
        return 0

    if not args.run:
        for i, draft in enumerate(queue, 1):
            print(f"{i:>3}. [{draft.collector}] {draft.title}")
        print(f"💡 Исполнение: `python {Path(__file__).absolute()} --run --repository owner/repo`")
        return 0

    service = _build_service(args)
    result = submit_queue(service, queue, max_tasks=args.max_tasks)
    print(f"📥 Подано: {len(result.submitted)}, пропущено дубликатов: {len(result.skipped_duplicates)}")
    for task_id in result.submitted:
        run = service.run_task(task_id)
        result.executed[task_id] = str(run.status)
        print(f"{'✅' if run.status == 'completed' else '⚠️'} {task_id}: {run.status}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
