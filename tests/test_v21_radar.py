"""v21.10 tests: Bounty Radar — приз из текста + свежие бесконкурентные алерты."""
import json
import sys
from datetime import datetime, timedelta, timezone

import pytest

sys.path.insert(0, "/root/AIOS")

from aios_core.gitcoin_algora_bounty_solver import (  # noqa: E402
    GitcoinAlgoraMasterSolver, extract_prize_usd)


def test_prize_parsing():
    assert extract_prize_usd("[Bounty $1,500] Generalize MSDA") == 1500.0
    assert extract_prize_usd("[Bounty $1500] x") == 1500.0
    assert extract_prize_usd("Reward $25k for perf", "") == 25000.0
    assert extract_prize_usd("no prize here") == 100.0
    assert extract_prize_usd("costs $0.10 per call") == 100.0  # слишком мало — дефолт
    assert extract_prize_usd("", "body says $200 reward") == 200.0
    assert extract_prize_usd("", "see $2 tip") == 100.0  # <$5 отбраковка


def _fresh(hours=1.0, prize_line="[Bounty $1,500] Fix X", prize_usd=None):
    b = {"id": f"gh_bounty_{abs(hash(prize_line)) % 99999}",
         "title": prize_line,
         "body": "",
         "html_url": "https://github.com/a/b/issues/9",
         "repository_url": "https://api.github.com/repos/a/b",
         "number": 9,
         "created_at": (datetime.now(timezone.utc)
                        - timedelta(hours=hours)).isoformat().replace("+00:00", "Z")}
    if prize_usd is not None:
        b["estimated_bounty_usd"] = prize_usd
    else:
        b["estimated_bounty_usd"] = extract_prize_usd(prize_line, "")
    return b


class FakeRadarEngine:
    def __init__(self, gate):
        self.gate = gate
        self.calls = 0

    def gate_for_bounty(self, bounty):
        self.calls += 1
        return self.gate


def _solver(tmp_path, monkeypatch, gate):
    solver = GitcoinAlgoraMasterSolver(data_dir=str(tmp_path))
    eng = FakeRadarEngine(gate)
    monkeypatch.setattr(solver, "_radar_engine", lambda: eng)
    sent = []
    monkeypatch.setattr(solver, "_notify", lambda text: sent.append(text))
    return solver, eng, sent


def test_radar_alerts_fresh_uncontested_once(tmp_path, monkeypatch):
    solver, eng, sent = _solver(tmp_path, monkeypatch,
                                {"status": "ok", "target_repo": "a/b", "issue_num": 9})
    b = _fresh(hours=2.0)
    r1 = solver.radar_sweep(bounties=[b])
    assert r1["fresh_uncontested"] == 1
    assert eng.calls == 1 and len(sent) == 1
    assert "Свежее бесконкурентное баунти" in sent[0]
    assert "$1,500" in sent[0] and "a/b#9" in sent[0]
    st = json.loads((tmp_path / "bounty_radar.json").read_text(encoding="utf-8"))
    assert st["seen"][b["id"]]["alerted"] is True
    # второй прогон — без повторного алерта и без вызова гейта
    r2 = solver.radar_sweep(bounties=[b])
    assert r2["fresh_uncontested"] == 0 and eng.calls == 1 and len(sent) == 1


def test_radar_no_alert_when_competition(tmp_path, monkeypatch):
    solver, eng, sent = _solver(tmp_path, monkeypatch,
                                {"status": "skip", "reason": "assignee: ['X']"})
    b = _fresh(hours=3.0)
    r = solver.radar_sweep(bounties=[b])
    assert r["fresh_uncontested"] == 0 and len(sent) == 0
    assert eng.calls == 1
    st = json.loads((tmp_path / "bounty_radar.json").read_text(encoding="utf-8"))
    assert "assignee" in st["seen"][b["id"]]["gate"]


def test_radar_stale_and_cheap_skip_engine(tmp_path, monkeypatch):
    solver, eng, sent = _solver(tmp_path, monkeypatch, {"status": "ok"})
    stale = _fresh(hours=300.0)
    cheap = _fresh(hours=1.0, prize_line="small fix $10")
    noca = _fresh(hours=1.0)
    noca["created_at"] = None
    r = solver.radar_sweep(bounties=[stale, cheap, noca])
    assert r["fresh_uncontested"] == 0
    assert eng.calls == 0  # гейт даже не вызывался
    assert len(sent) == 0


def test_radar_in_cycle_result(tmp_path, monkeypatch):
    """run_bounty_cycle возвращает ключ radar; баунти без created_at — без сети/TG."""
    solver = GitcoinAlgoraMasterSolver(data_dir=str(tmp_path))
    monkeypatch.setenv("AIOS_BOUNTY_PR", "off")
    bounty = {"id": "gh_t", "number": 1, "title": "t", "body": "b",
              "html_url": "https://github.com/o/r/issues/1",
              "repository_url": "https://api.github.com/repos/o/r",
              "comments_url": "https://api.github.com/repos/o/r/issues/1/comments"}
    monkeypatch.setattr(solver.scanner, "search_live_bounties",
                        lambda max_results=1: [bounty])
    monkeypatch.setattr(solver.balancer, "chat", lambda m, task_type="general": "ok")
    monkeypatch.setattr(solver.submitter, "post_issue_solution_comment",
                        lambda **kw: {"status": "success"})
    monkeypatch.setattr(solver.wallet, "record_income", lambda **kw: {})
    monkeypatch.setattr(solver.wallet, "get_financial_summary", lambda: {})
    res = solver.run_bounty_cycle(max_batch=1)
    assert "radar" in res and res["radar"]["fresh_uncontested"] == 0


# ---------------- v21.11: мультизапрос радара ----------------

def test_radar_queries_defaults_and_env(monkeypatch):
    from aios_core import gitcoin_algora_bounty_solver as sol
    monkeypatch.delenv("AIOS_BOUNTY_RADAR_QUERIES", raising=False)
    monkeypatch.delenv("AIOS_BOUNTY_WATCH_REPOS", raising=False)
    qs = sol.radar_queries()
    assert any("label:bounty" in q for q in qs)
    assert any("bounty in:title" in q for q in qs)
    assert any(q.startswith("repo:zhangjiayang6835-cyber/bounty-plaza") for q in qs)
    monkeypatch.setenv("AIOS_BOUNTY_RADAR_QUERIES", "label:x type:issue;; repo:y/z type:issue")
    assert sol.radar_queries() == ["label:x type:issue", "repo:y/z type:issue"]


def test_search_all_dedupe_newest_first(monkeypatch):
    from aios_core import gitcoin_algora_bounty_solver as sol

    class FakeScanner(sol.AlgoraGitcoinBountyScanner):
        def search_live_bounties(self, query="", max_results=3):
            base = {"title": "t", "body": "", "number": 1}
            if "python" in query:
                return [dict(base, id="a", html_url="u/a", created_at="2026-08-08T01:00:00Z"),
                        dict(base, id="b", html_url="u/b", created_at="2026-08-08T05:00:00Z")]
            return [dict(base, id="b2", html_url="u/b", created_at="2026-08-08T05:00:00Z"),  # дубль b
                    dict(base, id="c", html_url="u/c", created_at="2026-08-08T03:00:00Z")]

    monkeypatch.delenv("AIOS_BOUNTY_RADAR_QUERIES", raising=False)
    res = FakeScanner().search_all(max_results=10)
    keys = [b["id"] for b in res]
    assert len(keys) == len(set(keys)) == 3          # дедуп по html_url
    assert [b["created_at"] for b in res] == sorted(
        [b["created_at"] for b in res], reverse=True)  # новые первыми


def test_radar_sweep_prefers_search_all(tmp_path, monkeypatch):
    """radar_sweep вызывает search_all, если он есть у сканера."""
    solver = GitcoinAlgoraMasterSolver(data_dir=str(tmp_path))
    called = {}

    class FakeAll:
        def search_all(self, max_results=10):
            called["n"] = max_results
            return []

    solver.scanner = FakeAll()
    r = solver.radar_sweep()
    assert called.get("n") == 10 and r["scanned"] == 0


# ---------------- v21.12: качество сигнала ----------------

def test_prize_crypto_templates():
    assert extract_prize_usd("Fix bug", "Reward: 100 USDC via algora") == 100.0
    assert extract_prize_usd("Fix bug", "pays 250 USDT") == 250.0
    assert extract_prize_usd("Bounty 1,500 USDC", "") == 1500.0
    assert extract_prize_usd("$75 title wins", "999 USDC in body") == 75.0  # $ приоритет
    assert extract_prize_usd("nothing") == 100.0


def test_quality_line_tags():
    from aios_core.gitcoin_algora_bounty_solver import quality_line
    assert "🟢 топ-репо" in quality_line({"stars": 2500})
    assert "12.3k" in quality_line({"stars": 12345})
    assert "🟢 живой" in quality_line({"stars": 120})
    assert "🟡 мелкий" in quality_line({"stars": 3})
    assert quality_line({}) == ""


class _EngineWithQuality(FakeRadarEngine):
    def __init__(self, gate, quality):
        super().__init__(gate)
        self.quality = quality

    def repo_quality(self, owner, repo):
        return self.quality


def test_radar_archived_repo_skipped(tmp_path, monkeypatch):
    solver = GitcoinAlgoraMasterSolver(data_dir=str(tmp_path))
    eng = _EngineWithQuality({"status": "ok", "target_repo": "a/b", "issue_num": 9},
                             {"stars": 5, "archived": True})
    monkeypatch.setattr(solver, "_radar_engine", lambda: eng)
    sent = []
    monkeypatch.setattr(solver, "_notify", lambda text: sent.append(text))
    b = _fresh(hours=1.0)
    r = solver.radar_sweep(bounties=[b])
    assert r["fresh_uncontested"] == 0 and len(sent) == 0
    st = json.loads((tmp_path / "bounty_radar.json").read_text(encoding="utf-8"))
    assert "archived" in st["seen"][b["id"]]["gate"]


def test_radar_stars_recorded_and_line_in_alert(tmp_path, monkeypatch):
    solver = GitcoinAlgoraMasterSolver(data_dir=str(tmp_path))
    eng = _EngineWithQuality({"status": "ok", "target_repo": "a/b", "issue_num": 9},
                             {"stars": 1500, "archived": False})
    monkeypatch.setattr(solver, "_radar_engine", lambda: eng)
    sent = []
    monkeypatch.setattr(solver, "_notify", lambda text: sent.append(text))
    b = _fresh(hours=1.0)
    r = solver.radar_sweep(bounties=[b])
    assert r["fresh_uncontested"] == 1 and len(sent) == 1
    assert "⭐1.5k" in sent[0] and "🟢 топ-репо" in sent[0]
    st = json.loads((tmp_path / "bounty_radar.json").read_text(encoding="utf-8"))
    assert st["seen"][b["id"]]["stars"] == 1500


def test_radar_digest_when_three_plus(tmp_path, monkeypatch):
    solver = GitcoinAlgoraMasterSolver(data_dir=str(tmp_path))
    eng = _EngineWithQuality({"status": "ok", "target_repo": "a/b", "issue_num": 9},
                             {"stars": 7, "archived": False})
    monkeypatch.setattr(solver, "_radar_engine", lambda: eng)
    sent = []
    monkeypatch.setattr(solver, "_notify", lambda text: sent.append(text))
    bs = [_fresh(hours=float(i), prize_line=f"[Bounty $100] Fix {i}") for i in (1, 2, 3)]
    r = solver.radar_sweep(bounties=bs)
    assert r["fresh_uncontested"] == 3
    assert len(sent) == 1, "дайджест — одно сообщение"
    assert "Свежие бесконкурентные баунти: 3" in sent[0]
    assert sent[0].count("github.com/a/b/issues/9") == 3
