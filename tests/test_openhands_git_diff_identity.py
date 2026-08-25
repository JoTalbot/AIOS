from pathlib import Path
import subprocess

from aios_core.openhands.github import GitHubHelper


def _git(path: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=path, check=True, capture_output=True, text=True).stdout.strip()


def test_diff_hash_is_deterministic(tmp_path):
    _git(tmp_path, "init", "-b", "main")
    _git(tmp_path, "config", "user.email", "test@example.com")
    _git(tmp_path, "config", "user.name", "AIOS Test")
    (tmp_path / "a.txt").write_text("one\n", encoding="utf-8")
    _git(tmp_path, "add", "a.txt")
    _git(tmp_path, "commit", "-m", "base")
    helper = GitHubHelper(tmp_path)
    helper.create_branch("feature", "main")
    (tmp_path / "a.txt").write_text("two\n", encoding="utf-8")
    first = helper.diff_hash("main")
    second = helper.diff_hash("main")
    assert first == second
    assert len(first) == 64


def test_diff_hash_changes_when_diff_changes(tmp_path):
    _git(tmp_path, "init", "-b", "main")
    _git(tmp_path, "config", "user.email", "test@example.com")
    _git(tmp_path, "config", "user.name", "AIOS Test")
    (tmp_path / "a.txt").write_text("one\n", encoding="utf-8")
    _git(tmp_path, "add", "a.txt")
    _git(tmp_path, "commit", "-m", "base")
    helper = GitHubHelper(tmp_path)
    helper.create_branch("feature", "main")
    (tmp_path / "a.txt").write_text("two\n", encoding="utf-8")
    first = helper.diff_hash("main")
    (tmp_path / "a.txt").write_text("three\n", encoding="utf-8")
    assert helper.diff_hash("main") != first
