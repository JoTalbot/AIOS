"""Тесты GitHubHelper: git-операции против реального tmp-репозитория.

Без моков: реальный git в tmp_path; PR API — через DI api_opener
(реальный urllib-код разбора ответа, без сети).
"""

import io
import json
import subprocess
import urllib.error

import pytest

from aios_core.openhands import GitHubHelper, GitOperationError, OpenHandsAPIError


@pytest.fixture
def repo(tmp_path):
    subprocess.run(["git", "init", "-b", "main"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "t@t"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=tmp_path, check=True)
    (tmp_path / "base.txt").write_text("base")
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=tmp_path, check=True, capture_output=True)
    return tmp_path


class FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class TestGit:
    def test_create_branch_and_switch_back(self, repo):
        gh = GitHubHelper(repo)
        gh.create_branch("agent/oh-t1")
        assert gh.current_branch() == "agent/oh-t1"
        # Идемпотентно: повторный вызов не падает.
        gh.create_branch("agent/oh-t1")
        assert gh.current_branch() == "agent/oh-t1"

    def test_commit_paths_and_changed_files(self, repo):
        gh = GitHubHelper(repo)
        gh.create_branch("agent/oh-t2")
        (repo / "feature.py").write_text("x = 1\n")
        (repo / "other.txt").write_text("staged?\n")
        sha = gh.commit_paths(["feature.py"], "oh(t2): add feature")
        assert sha
        # other.txt не закоммичен — коммитим только свои пути.
        assert gh.changed_files("main") == ["feature.py"]
        status = gh.git.run("status", "--porcelain").stdout
        assert "other.txt" in status

    def test_commit_paths_no_changes_returns_none(self, repo):
        gh = GitHubHelper(repo)
        gh.create_branch("agent/oh-t3")
        assert gh.commit_paths(["base.txt"], "nothing") is None

    def test_failed_git_raises_short_message(self, repo):
        gh = GitHubHelper(repo)
        with pytest.raises(GitOperationError):
            gh.git.run("checkout", "nonexistent-branch")


class TestPullRequest:
    def test_create_pr_payload(self, repo):
        captured = {}

        def opener(request):
            captured["url"] = request.full_url
            captured["body"] = json.loads(request.data.decode())
            captured["auth"] = request.headers.get("Authorization")
            return FakeResponse(json.dumps({"html_url": "https://x/pr/1", "number": 1}).encode())

        gh = GitHubHelper(repo, repo_slug="JoTalbot/AIOS", token="t", api_opener=opener)
        result = gh.create_pull_request(branch="agent/oh-t1", title="T", body="B")
        assert result["html_url"] == "https://x/pr/1"
        assert captured["url"] == "https://api.github.com/repos/JoTalbot/AIOS/pulls"
        assert captured["body"]["head"] == "agent/oh-t1"
        assert captured["body"]["draft"] is True

    def test_pr_without_credentials_raises(self, repo):
        gh = GitHubHelper(repo)
        with pytest.raises(OpenHandsAPIError):
            gh.create_pull_request(branch="b", title="t", body="b")

    def test_pr_http_error_masked(self, repo):
        def opener(request):
            raise urllib.error.HTTPError(request.full_url, 422, "err", {}, io.BytesIO(b'{"message":"bad"}'))

        gh = GitHubHelper(repo, repo_slug="o/r", token="t", api_opener=opener)
        with pytest.raises(OpenHandsAPIError) as exc:
            gh.create_pull_request(branch="b", title="t", body="b")
        assert exc.value.status_code == 422


class TestBranchSync:
    """prepare/sync ветки для связки с Cloud (агенты пушат в remote)."""

    def test_prepare_branch_pushes_when_remote_exists(self, repo, tmp_path):
        remote = tmp_path / "remote.git"
        subprocess.run(["git", "init", "--bare", str(remote)], check=True, capture_output=True)
        subprocess.run(["git", "remote", "add", "origin", str(remote)], cwd=repo, check=True)

        gh = GitHubHelper(repo)
        gh.prepare_branch("agent/oh-x")
        out = subprocess.run(
            ["git", "ls-remote", "--heads", "origin", "agent/oh-x"],
            cwd=repo, check=True, capture_output=True, text=True,
        )
        assert "agent/oh-x" in out.stdout

    def test_prepare_branch_without_remote_is_local_only(self, repo):
        gh = GitHubHelper(repo)
        gh.prepare_branch("agent/oh-y")
        assert gh.current_branch() == "agent/oh-y"

    def test_sync_branch_picks_remote_changes(self, repo, tmp_path):
        remote = tmp_path / "remote.git"
        subprocess.run(["git", "init", "--bare", str(remote)], check=True, capture_output=True)
        subprocess.run(["git", "remote", "add", "origin", str(remote)], cwd=repo, check=True)
        gh = GitHubHelper(repo)
        gh.prepare_branch("agent/oh-z")

        # «Cloud-агент»: клонирует, коммитит и пушит в ветку.
        other = tmp_path / "cloud_clone"
        subprocess.run(["git", "clone", str(remote), str(other)], check=True, capture_output=True)
        subprocess.run(["git", "config", "user.email", "c@c"], cwd=other, check=True)
        subprocess.run(["git", "config", "user.name", "c"], cwd=other, check=True)
        subprocess.run(["git", "checkout", "agent/oh-z"], cwd=other, check=True, capture_output=True)
        (other / "cloud_change.py").write_text("x = 1\n")
        subprocess.run(["git", "add", "."], cwd=other, check=True)
        subprocess.run(["git", "commit", "-m", "cloud change"], cwd=other, check=True, capture_output=True)
        subprocess.run(["git", "push"], cwd=other, check=True, capture_output=True)

        assert not (repo / "cloud_change.py").exists()
        gh.sync_branch("agent/oh-z")
        assert (repo / "cloud_change.py").exists()
        assert gh.changed_files("main") == ["cloud_change.py"]

    def test_sync_branch_without_remote_is_noop(self, repo):
        gh = GitHubHelper(repo)
        gh.create_branch("agent/oh-w")
        gh.sync_branch("agent/oh-w")  # не падает
        assert gh.current_branch() == "agent/oh-w"
