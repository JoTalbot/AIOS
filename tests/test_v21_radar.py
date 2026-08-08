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
