"""v21.6 tests: BountySolutionEngine гейты + проводка солвера (без фантомного дохода)."""
import sys

import pytest

sys.path.insert(0, "/root/AIOS")

from aios_core.bounty_solution_engine import BountySolutionEngine, MAX_FILES  # noqa: E402


CANNED = '''PR_TITLE: fix: repair parser crash
PR_BODY:
## Что сделано
Починил парсер.

## Как проверено
- pytest

FILE: src/parser.py
REASON: main fix
<<CONTENT>>
def parse(x):
    return x
<<END_FILE>>
FILE: .github/workflows/ci.yml
<<CONTENT>>
on: push
<<END_FILE>>
FILE: docs/NOTE.md
<<CONTENT>>
# note
<<END_FILE>>
FILE: extra1.py
<<CONTENT>>
x=1
<<END_FILE>>
FILE: extra2.py
<<CONTENT>>
x=2
<<END_FILE>>
ANALYSIS: Fix broken parser

'''


class FakeBuilder:
    """Записывает вызовы build_pr; GET repo meta отвечает."""

    def __init__(self):
        self.calls = []
        self.dry_run = True

    def gh(self, method, path, payload=None, timeout=20):
        if path.startswith("/repos/owner/repo") and "contents" not in path:
            return {"default_branch": "main"}, None
        if "contents" in path:
            return [{"path": "src", "type": "dir"}, {"path": "README.md", "type": "file"}], None
        return None, {"status": 404}

    def build_pr(self, **kw):
        self.calls.append(kw)
        return {"status": "dry_run" if self.dry_run else "created",
                "url": "https://gh/pr/1", "steps": ["ok"]}


class FakeBalancer:
    def __init__(self, text=CANNED):
        self.text = text

    def chat(self, messages, task_type="general"):
        return self.text


BOUNTY = {"id": "gh_1", "number": 42, "title": "Crash", "body": "it crashes",
          "html_url": "https://github.com/owner/repo/issues/42",
          "repository_url": "https://api.github.com/repos/owner/repo",
          "comments_url": "https://api.github.com/repos/owner/repo/issues/42/comments"}


def test_engine_gates_and_branch():
    b = FakeBuilder()
    eng = BountySolutionEngine(balancer=FakeBalancer(), pr_builder=b)
    r = eng.solve_and_pr(BOUNTY, dry_run=True)

    assert r["status"] == "dry_run"
    assert r["branch"] == "aios/bounty-42"
    kw = b.calls[0]
    # banned .github/workflows отфильтрован, лимит MAX_FILES соблюдён
    assert len(kw["file_changes"]) == MAX_FILES
    assert ".github/workflows/ci.yml" not in kw["file_changes"]
    assert "src/parser.py" in kw["file_changes"]
    assert any("unsafe/banned" in s for s in r["skipped"]) or any("лимит" in s for s in r["skipped"])
    # body содержит подпись AIOS
    assert "AIOS Bounty Engine" in kw["pr_body"]
    assert kw["base_branch"] == "main" and kw["upstream_owner"] == "owner"


def test_engine_llm_json_failure():
    eng = BountySolutionEngine(balancer=FakeBalancer("это не json вовсе"), pr_builder=FakeBuilder())
    r = eng.solve_and_pr(BOUNTY, dry_run=True)
    assert r["status"] == "error"


def test_engine_all_files_rejected():
    bad = ('PR_TITLE: x\n'
           'FILE: .git/config\n<<CONTENT>>\nz\n<<END_FILE>>\n'
           'FILE: ../evil\n<<CONTENT>>\nz\n<<END_FILE>>\n')
    eng = BountySolutionEngine(balancer=FakeBalancer(bad), pr_builder=FakeBuilder())
    r = eng.solve_and_pr(BOUNTY, dry_run=True)
    assert r["status"] == "error" and "rejected" in r["error"]


def test_solver_cycle_no_phantom_income(tmp_path, monkeypatch):
    """Цикл солвера: потенциал фиксируется, wallet.record_income НЕ вызывается."""
    import os
    from aios_core.gitcoin_algora_bounty_solver import GitcoinAlgoraMasterSolver

    monkeypatch.setenv("AIOS_BOUNTY_PR", "off")  # явно: иначе сработает .env-fallback
    solver = GitcoinAlgoraMasterSolver(data_dir=str(tmp_path))
    monkeypatch.setattr(solver.scanner, "search_live_bounties", lambda max_results=1: [BOUNTY])
    monkeypatch.setattr(solver.balancer, "chat", lambda m, task_type="general": "Решение тут")
    monkeypatch.setattr(solver.submitter, "post_issue_solution_comment",
                        lambda **kw: {"status": "success", "comment_id": 1})
    income_calls = []
    monkeypatch.setattr(solver.wallet, "record_income", lambda **kw: income_calls.append(kw) or {})
    monkeypatch.setattr(solver.wallet, "get_financial_summary", lambda: {})

    res = solver.run_bounty_cycle(max_batch=1)
    assert income_calls == [], "record_income не должен вызываться на отклик"
    one = res["solved_results"][0]
    assert one["potential_usd"] == 100.0
    assert one["pr_result"] is None  # AIOS_BOUNTY_PR=off по умолчанию


def test_solver_cycle_pr_plan_hook(tmp_path, monkeypatch):
    """AIOS_BOUNTY_PR=plan → в цикле появляется pr_result dry_run."""
    from aios_core.gitcoin_algora_bounty_solver import GitcoinAlgoraMasterSolver

    monkeypatch.setenv("AIOS_BOUNTY_PR", "plan")
    solver = GitcoinAlgoraMasterSolver(data_dir=str(tmp_path))
    monkeypatch.setattr(solver.scanner, "search_live_bounties", lambda max_results=1: [BOUNTY])
    monkeypatch.setattr(solver.balancer, "chat", lambda m, task_type="general": CANNED)
    monkeypatch.setattr(solver.submitter, "post_issue_solution_comment",
                        lambda **kw: {"status": "success"})
    monkeypatch.setattr(solver.wallet, "record_income", lambda **kw: {})
    monkeypatch.setattr(solver.wallet, "get_financial_summary", lambda: {})

    # движок на фейковый builder
    import aios_core.bounty_solution_engine as bse
    monkeypatch.setattr(bse, "BountyPRBuilder", lambda *a, **k: FakeBuilder())

    res = solver.run_bounty_cycle(max_batch=1)
    pr = res["solved_results"][0]["pr_result"]
    assert pr is not None and pr["status"] == "dry_run"
    assert pr["branch"] == "aios/bounty-42"


def test_engine_bold_fence_style():
    """groq оборачивает маркеры в **болд** и шлёт контент в ```фенсах```."""
    groq_style = (
        "**PR_TITLE:** fix: gen multi_scale D\n\n"
        "**PR_BODY:**\n## Что сделано\nОк.\n\n"
        "**FILE:** src/gen.py\n\n**REASON:** основной фикс\n\n"
        "```python\nx = 1\ny = 2\n```\n\n"
        "ANALYSIS: done\n"
    )
    b = FakeBuilder()
    eng = BountySolutionEngine(balancer=FakeBalancer(groq_style), pr_builder=b)
    r = eng.solve_and_pr(BOUNTY, dry_run=True)
    assert r["status"] == "dry_run"
    kw = b.calls[0]
    assert kw["file_changes"]["src/gen.py"] == "x = 1\ny = 2"
    assert kw["pr_title"].startswith("fix:")
