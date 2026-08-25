"""Git/GitHub-операции OpenHands-контура.

Подкоманды git выполняются через subprocess внутри локального рабочего дерева
(ветки/коммиты/diff), PR — через GitHub REST API. Секреты в лог не выводятся:
stderr обрезается до 300 символов, токен нигде не форматируется.
"""

from __future__ import annotations

import json
import subprocess
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

from .errors import OpenHandsAPIError


class GitOperationError(RuntimeError):
    """Ошибка git/GitHub операции контура."""


def _short(text: str, limit: int = 300) -> str:
    text = (text or "").strip()
    return text if len(text) <= limit else text[:limit] + "…"


@dataclass
class GitRunner:
    """Выполнение git-команд в рабочем дереве (без shell, список аргументов)."""

    repo_path: Path

    def run(self, *args: str, check: bool = True) -> subprocess.CompletedProcess:
        proc = subprocess.run(
            ["git", *args],
            cwd=self.repo_path,
            capture_output=True,
            text=True,
            timeout=60,
        )
        if check and proc.returncode != 0:
            raise GitOperationError(f"git {' '.join(args)}: {_short(proc.stderr)}")
        return proc


@dataclass
class GitHubHelper:
    """Ветка, коммит, diff, PR для задачи контура.

    Args:
        repo_path: локальное рабочее дерево.
        repo_slug: ``owner/repo`` для PR API.
        token: GitHub token (не логируется).
        api_opener: DI для тестов (urlopen-compatible callable).
    """

    repo_path: Path
    repo_slug: str = ""
    token: str = ""
    api_opener: object = urllib.request.urlopen
    git: GitRunner = field(init=False)

    def __post_init__(self) -> None:
        self.git = GitRunner(Path(self.repo_path))

    # ── git ───────────────────────────────────────────────────────

    def create_branch(self, branch: str, base: str = "main") -> str:
        """Создать feature-ветку от base (idempotent: существующая не ошибка)."""
        exists = self.git.run("rev-parse", "--verify", branch, check=False)
        if exists.returncode == 0:
            self.git.run("checkout", branch)
        else:
            self.git.run("checkout", "-b", branch, base)
        return branch

    def current_branch(self) -> str:
        """Имя текущей ветки."""
        return self.git.run("rev-parse", "--abbrev-ref", "HEAD").stdout.strip()

    def commit_paths(self, paths: list[str], message: str) -> str | None:
        """Закоммитить указанные пути (git add <paths> + commit).

        Возвращает sha коммита или None, если изменений нет.
        """
        self.git.run("add", "--", *paths)
        if self.git.run("diff", "--cached", "--quiet", check=False).returncode == 0:
            return None
        self.git.run("commit", "-m", message)
        return self.git.run("rev-parse", "HEAD").stdout.strip()

    def changed_files(self, base: str = "main") -> list[str]:
        """Файлы, изменённые веткой относительно base (name-only)."""
        out = self.git.run("diff", "--name-only", f"{base}...HEAD").stdout
        return [line.strip() for line in out.splitlines() if line.strip()]

    def push_branch(self, branch: str, remote: str = "origin") -> None:
        """Push ветки с tracking."""
        self.git.run("push", "-u", remote, branch)

    def has_remote(self, remote: str = "origin") -> bool:
        """Есть ли настроенный remote (в тестах локальных репо его нет)."""
        return self.git.run("remote", "get-url", remote, check=False).returncode == 0

    def prepare_branch(self, branch: str, base: str = "main", remote: str = "origin") -> str:
        """Создать ветку от base и запушить (если remote настроен).

        Cloud-разговоры клонируют репозиторий по ``selected_branch`` — ветка
        обязана существовать на remote до старта стадий.
        """
        self.create_branch(branch, base)
        if self.has_remote(remote):
            self.push_branch(branch, remote)
        return branch

    def sync_branch(self, branch: str, remote: str = "origin") -> None:
        """Подтянуть состояние ветки с remote.

        Cloud-агенты пушат изменения в ветку; локальное дерево перед diff
        обязано отражать remote (workspace — выделенный клон контура,
        reset --hard в нём безопасен).
        """
        if not self.has_remote(remote):
            return
        self.git.run("fetch", remote, branch)
        exists = self.git.run("rev-parse", "--verify", branch, check=False)
        if exists.returncode == 0:
            self.git.run("checkout", branch)
        else:
            self.git.run("checkout", "-b", branch, f"{remote}/{branch}")
        self.git.run("reset", "--hard", f"{remote}/{branch}")

    # ── GitHub API ────────────────────────────────────────────────

    def create_pull_request(
        self,
        *,
        branch: str,
        title: str,
        body: str,
        base: str = "main",
        draft: bool = True,
    ) -> dict:
        """Создать (draft) PR через GitHub REST API."""
        if not self.repo_slug or not self.token:
            raise OpenHandsAPIError("для PR нужны repo_slug и token")
        payload = json.dumps(
            {"title": title, "head": branch, "base": base, "body": body, "draft": draft}
        ).encode()
        request = urllib.request.Request(
            f"https://api.github.com/repos/{self.repo_slug}/pulls",
            data=payload,
            headers={
                "Authorization": f"Bearer {self.token}",
                "Accept": "application/vnd.github+json",
                "Content-Type": "application/json",
            },
        )
        try:
            with self.api_opener(request) as response:  # type: ignore[misc]
                return json.loads(response.read().decode())
        except urllib.error.HTTPError as exc:
            raise OpenHandsAPIError(
                f"GitHub PR API HTTP {exc.code}: {_short(exc.read().decode(errors='replace'))}",
                status_code=exc.code,
            ) from exc
