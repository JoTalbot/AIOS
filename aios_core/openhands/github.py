"""Git/GitHub-операции OpenHands-контура.

Подкоманды git выполняются через subprocess внутри локального рабочего дерева
(ветки/коммиты/diff), PR — через GitHub REST API. Секреты в лог не выводятся:
stderr обрезается до 300 символов, токен нигде не форматируется.
"""

from __future__ import annotations

import hashlib
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
    repo_path: Path

    def run(self, *args: str, check: bool = True) -> subprocess.CompletedProcess:
        proc = subprocess.run(["git", *args], cwd=self.repo_path, capture_output=True, text=True, timeout=60)
        if check and proc.returncode != 0:
            raise GitOperationError(f"git {' '.join(args)}: {_short(proc.stderr)}")
        return proc


@dataclass
class GitHubHelper:
    repo_path: Path
    repo_slug: str = ""
    token: str = ""
    api_opener: object = urllib.request.urlopen
    git: GitRunner = field(init=False)

    def __post_init__(self) -> None:
        self.git = GitRunner(Path(self.repo_path))

    def create_branch(self, branch: str, base: str = "main") -> str:
        exists = self.git.run("rev-parse", "--verify", branch, check=False)
        if exists.returncode == 0:
            self.git.run("checkout", branch)
        else:
            self.git.run("checkout", "-b", branch, base)
        return branch

    def current_branch(self) -> str:
        return self.git.run("rev-parse", "--abbrev-ref", "HEAD").stdout.strip()

    def head_sha(self) -> str:
        """Точный SHA текущего HEAD."""
        return self.git.run("rev-parse", "HEAD").stdout.strip()

    def commit_paths(self, paths: list[str], message: str) -> str | None:
        self.git.run("add", "--", *paths)
        if self.git.run("diff", "--cached", "--quiet", check=False).returncode == 0:
            return None
        self.git.run("commit", "-m", message)
        return self.head_sha()

    def changed_files(self, base: str = "main") -> list[str]:
        out = self.git.run("diff", "--name-only", f"{base}...HEAD").stdout
        return [line.strip() for line in out.splitlines() if line.strip()]

    def diff_hash(self, base: str = "main") -> str:
        """SHA-256 canonical hash of the exact branch diff against base."""
        diff = self.git.run("diff", "--binary", "--full-index", f"{base}...HEAD").stdout
        return hashlib.sha256(diff.encode("utf-8", errors="surrogateescape")).hexdigest()

    def push_branch(self, branch: str, remote: str = "origin") -> None:
        self.git.run("push", "-u", remote, branch)

    def has_remote(self, remote: str = "origin") -> bool:
        return self.git.run("remote", "get-url", remote, check=False).returncode == 0

    def prepare_branch(self, branch: str, base: str = "main", remote: str = "origin") -> str:
        self.create_branch(branch, base)
        if self.has_remote(remote):
            self.push_branch(branch, remote)
        return branch

    def sync_branch(self, branch: str, remote: str = "origin") -> None:
        if not self.has_remote(remote):
            return
        self.git.run("fetch", remote, branch)
        exists = self.git.run("rev-parse", "--verify", branch, check=False)
        if exists.returncode == 0:
            self.git.run("checkout", branch)
        else:
            self.git.run("checkout", "-b", branch, f"{remote}/{branch}")
        self.git.run("reset", "--hard", f"{remote}/{branch}")

    def create_pull_request(self, *, branch: str, title: str, body: str, base: str = "main", draft: bool = True) -> dict:
        if not self.repo_slug or not self.token:
            raise OpenHandsAPIError("для PR нужны repo_slug и token")
        payload = json.dumps({"title": title, "head": branch, "base": base, "body": body, "draft": draft}).encode()
        request = urllib.request.Request(
            f"https://api.github.com/repos/{self.repo_slug}/pulls",
            data=payload,
            headers={"Authorization": f"Bearer {self.token}", "Accept": "application/vnd.github+json", "Content-Type": "application/json"},
        )
        try:
            with self.api_opener(request) as response:
                return json.loads(response.read().decode())
        except urllib.error.HTTPError as exc:
            raise OpenHandsAPIError(f"GitHub PR API HTTP {exc.code}: {_short(exc.read().decode(errors='replace'))}", status_code=exc.code) from exc
