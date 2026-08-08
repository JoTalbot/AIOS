"""v21.5 PR-mode tests: dry-run plan, цепочка REST, already_exists, валидация."""
import sys

import pytest

sys.path.insert(0, "/root/AIOS")

from aios_core.bounty_pr_builder import BountyPRBuilder  # noqa: E402


class FakeTransport(BountyPRBuilder):
    """Транспорт-заглушка: записывает вызовы, живые ответы по скрипту."""

    def __init__(self, script, **kw):
        super().__init__(github_token="t", **kw)
        self.script = script          # {(method, path_prefix): response}
        self.calls = []

    def gh(self, method, path, payload=None, timeout=20):
        self.calls.append((method, path))
        # самый длинный префикс — специфичные пути не должны съедаться общими
        for (m, pref), resp in sorted(self.script.items(),
                                      key=lambda kv: -len(kv[0][1])):
            if method == m and path.startswith(pref):
                return resp, None
        return None, {"status": 404, "message": f"unscripted: {method} {path}"}


BASE_SCRIPT = {
    ("GET", "/user"): {"login": "bot"},
    ("GET", "/repos/owner/upstream/pulls"): [],
    ("GET", "/repos/bot/upstream"): {"full_name": "bot/upstream"},
    ("GET", "/repos/bot/upstream/git/ref/heads/main"): {"object": {"sha": "a" * 40}},
    ("GET", "/repos/bot/upstream/git/commits/"): {"tree": {"sha": "t" * 40}},
    ("POST", "/repos/bot/upstream/git/blobs"): {"sha": "b" * 40},
    ("POST", "/repos/bot/upstream/git/trees"): {"sha": "c" * 40},
    ("POST", "/repos/bot/upstream/git/commits"): {"sha": "d" * 40},
    ("POST", "/repos/bot/upstream/git/refs"): {"ref": "refs/heads/aios/b-1"},
    ("POST", "/repos/owner/upstream/pulls"): {"html_url": "https://gh/pr/1", "number": 1},
}


def test_dry_run_writes_nothing():
    b = FakeTransport(BASE_SCRIPT, dry_run=True)
    r = b.build_pr("owner", "upstream", "main",
                   {"fix.py": "print('fixed')\n"}, "aios/b-1", "fix: title", "body")
    assert r["status"] == "dry_run"
    assert all(m == "GET" for m, _ in b.calls), "в dry-run не должно быть записей"
    assert any("PR" in s or "POST" in s for s in r["steps"])  # план присутствует


def test_live_created_chain_order():
    b = FakeTransport(BASE_SCRIPT, dry_run=False)
    r = b.build_pr("owner", "upstream", "main",
                   {"a.py": "1\n", "b.py": "2\n"}, "aios/b-1", "fix: x", "body")
    assert r["status"] == "created" and r["url"] == "https://gh/pr/1"
    methods = [m for m, p in b.calls if m != "GET"]
    # forks policy: fork exists → без POST /forks; дальше blobs(2)→tree→commit→ref→PR
    assert all("/forks" not in p for m, p in b.calls if m == "POST")
    assert methods == ["POST", "POST", "POST", "POST", "POST", "POST"]
    assert r["steps"][-1].startswith("PR created")


def test_existing_pr_not_duplicated():
    script = dict(BASE_SCRIPT)
    script[("GET", "/repos/owner/upstream/pulls")] = [
        {"head": {"user": {"login": "bot"}, "ref": "aios/b-1"}, "html_url": "https://gh/pr/9"}]
    b = FakeTransport(script, dry_run=False)
    r = b.build_pr("owner", "upstream", "main", {"a.py": "1\n"}, "aios/b-1", "t", "b")
    assert r["status"] == "already_exists" and r["url"] == "https://gh/pr/9"
    assert all(m == "GET" for m, _ in b.calls), "при существующем PR записей быть не должно"


def test_validation_rejects_bad_input():
    b = FakeTransport(BASE_SCRIPT, dry_run=False)
    assert b.build_pr("o", "r", "main", {}, "aios/x", "t", "b")["status"] == "error"
    assert b.build_pr("o", "r", "main", {"../evil": "x"}, "aios/x", "t", "b")["status"] == "error"
    assert b.build_pr("o", "r", "main", {"a.py": "   "}, "aios/x", "t", "b")["status"] == "error"
    assert b.build_pr("o", "r", "main", {"a.py": "x\n"}, "bad branch!", "t", "b")["status"] == "error"


class TestLiveGateResolution:
    """v21.13: единый live-гейт (plan→live по одобрению владельца)."""

    def test_live_via_env(self, monkeypatch):
        monkeypatch.setenv("AIOS_BOUNTY_PR", "live")
        monkeypatch.delenv("AIOS_BOUNTY_PR_MODE", raising=False)
        b = BountyPRBuilder(github_token="t")
        assert b.dry_run is False

    def test_plan_via_env(self, monkeypatch):
        monkeypatch.setenv("AIOS_BOUNTY_PR", "plan")
        monkeypatch.delenv("AIOS_BOUNTY_PR_MODE", raising=False)
        b = BountyPRBuilder(github_token="t")
        assert b.dry_run is True

    def test_live_via_dotenv_fallback(self, monkeypatch, tmp_path):
        import aios_core.bounty_pr_builder as bpb
        monkeypatch.delenv("AIOS_BOUNTY_PR", raising=False)
        monkeypatch.delenv("AIOS_BOUNTY_PR_MODE", raising=False)
        env = tmp_path / ".env"
        env.write_text("# comment line\nAIOS_BOUNTY_PR=live\n", encoding="utf-8")
        monkeypatch.setattr(bpb, "DEFAULT_ENV_FILE", str(env))
        b = BountyPRBuilder(github_token="t")
        assert b.dry_run is False

    def test_live_with_trailing_comment(self, monkeypatch):
        monkeypatch.setenv("AIOS_BOUNTY_PR", "live  # approved")
        monkeypatch.delenv("AIOS_BOUNTY_PR_MODE", raising=False)
        b = BountyPRBuilder(github_token="t")
        assert b.dry_run is False

    def test_legacy_mode_still_works(self, monkeypatch):
        monkeypatch.setenv("AIOS_BOUNTY_PR_MODE", "1")
        monkeypatch.delenv("AIOS_BOUNTY_PR", raising=False)
        b = BountyPRBuilder(github_token="t")
        assert b.dry_run is False
