"""v21.6/v21.7 tests: BountySolutionEngine гейты + проводка солвера +
полный файловый контекст (v21.7)."""
import base64
import sys

import pytest

sys.path.insert(0, "/root/AIOS")

from aios_core.bounty_solution_engine import (  # noqa: E402
    BountySolutionEngine, MAX_FILES, _score_path, _issue_tokens)


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
        self.last_messages = None
        self.last_task_type = None

    def chat(self, messages, task_type="general"):
        self.last_messages = messages
        self.last_task_type = task_type
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


# ---------------- v21.7: полный файловый контекст ----------------

TREE_FAKE = {"tree": [
    {"path": "src/parser.py", "type": "blob"},
    {"path": "src/lexer.py", "type": "blob"},
    {"path": "docs/guide.md", "type": "blob"},
    {"path": "README.md", "type": "blob"},
    {"path": "tests/test_parser.py", "type": "blob"},
    {"path": "src", "type": "tree"},
]}

BOUNTY_P = dict(BOUNTY, title="Parser crash when reading lexer output",
                body="The parser module fails on tokens from the lexer, see traceback")


class FakeBuilderV2(FakeBuilder):
    """Добавляет рекурсивное дерево и контент файлов (contents API, base64)."""

    def gh(self, method, path, payload=None, timeout=20):
        if "git/trees" in path:
            return dict(TREE_FAKE), None
        if "contents/" in path and "ref=" in path:
            fname = path.split("contents/")[1].split("?")[0]
            code = f"# content of {fname}\nCRASH = True\n"
            return {"encoding": "base64",
                    "content": base64.b64encode(code.encode()).decode()}, None
        return super().gh(method, path, payload, timeout)


def test_v217_scoring_and_tokens():
    tokens = _issue_tokens(BOUNTY_P)
    assert "parser" in tokens and "lexer" in tokens
    assert "parser" in _issue_tokens({"title": "x", "body": "Parser"})  # case-insens
    assert _score_path("src/parser.py", tokens) > _score_path("README.md", tokens)
    assert _score_path("src/lexer.py", tokens) > 0
    assert _score_path("docs/guide.md", tokens) <= 0


def test_v217_context_files_selected_and_in_prompt():
    bal = FakeBalancer()
    eng = BountySolutionEngine(balancer=bal, pr_builder=FakeBuilderV2())
    r = eng.solve_and_pr(BOUNTY_P, dry_run=True)
    assert r["status"] == "dry_run"
    assert "src/parser.py" in r["context_files"]
    assert "src/lexer.py" in r["context_files"]
    prompt = bal.last_messages[0]["content"]
    assert "ИСХОДНЫЙ КОД РЕЛЕВАНТНЫХ ФАЙЛОВ" in prompt
    assert "CRASH = True" in prompt  # реальный код файла в промпте
    assert "базируй CONTENT СТРОГО" in prompt


def test_v217_context_budget(monkeypatch):
    import aios_core.bounty_solution_engine as bse
    monkeypatch.setattr(bse, "PER_FILE_CONTEXT_BYTES", 10)
    monkeypatch.setattr(bse, "CONTEXT_MAX_BYTES", 15)
    eng = BountySolutionEngine(balancer=FakeBalancer(), pr_builder=FakeBuilderV2())
    ctx = eng.fetch_context("owner", "repo", "main",
                            ["src/parser.py", "src/lexer.py", "x.py"])
    assert sum(len(v) for v in ctx.values()) <= 15
    assert all(len(v) <= 10 for v in ctx.values())


def test_v217_no_tree_fallback_to_root_paths():
    """Старый FakeBuilder без дерева → контекст пустой, план всё равно строится."""
    eng = BountySolutionEngine(balancer=FakeBalancer(), pr_builder=FakeBuilder())
    r = eng.solve_and_pr(BOUNTY, dry_run=True)
    assert r["status"] == "dry_run"
    assert r["context_files"] == []


# ---------------- v21.8: резолв целевого репо + явные пути + retry ----------------

BOUNTY_PLATFORM = {
    "id": "gh_p1", "number": 802,
    "title": "[Bounty $1,500] Some task",
    "body": ("### Source URL\nhttps://github.com/acme/widgets/issues/52328\n\n"
             "## Description\nFix thing"),
    "html_url": "https://github.com/zhang/bounty-plaza/issues/802",
    "repository_url": "https://api.github.com/repos/zhang/bounty-plaza",
}

TARGET_ISSUE_BODY = ("Crash in `src/widgets/engine.cpp:68-74` when D=64.\n"
                     "See also docs for context.")


class FakeBuilderV3(FakeBuilder):
    """Платформа + целевой репозиторий acme/widgets с issue #52328."""

    def gh(self, method, path, payload=None, timeout=20):
        if path.startswith("/repos/acme/widgets/issues/"):
            return {"title": "Engine crash D=64", "body": TARGET_ISSUE_BODY,
                    "html_url": "https://github.com/acme/widgets/issues/52328"}, None
        if path.startswith("/repos/acme/widgets") and "contents" not in path \
                and "git/trees" not in path:
            return {"default_branch": "main"}, None
        if "git/trees" in path:
            return {"tree": [
                {"path": "src/widgets/engine.cpp", "type": "blob"},
                {"path": "src/widgets/engine.hpp", "type": "blob"},
                {"path": "docs/manual.md", "type": "blob"},
            ]}, None
        if "contents/" in path and "ref=" in path:
            fname = path.split("contents/")[1].split("?")[0]
            code = f"// code of {fname}\nTT_FATAL(D == 32);\n"
            return {"encoding": "base64",
                    "content": base64.b64encode(code.encode()).decode()}, None
        if "contents" in path:
            return [{"path": "src", "type": "dir"}, {"path": "docs", "type": "dir"}], None
        return None, {"status": 404}


def test_v218_target_repo_resolution():
    bal = FakeBalancer()
    b = FakeBuilderV3()
    eng = BountySolutionEngine(balancer=bal, pr_builder=b)
    r = eng.solve_and_pr(BOUNTY_PLATFORM, dry_run=True)
    assert r["status"] == "dry_run"
    assert r["target_repo"] == "acme/widgets"  # не bounty-plaza!
    kw = b.calls[0]
    assert kw["upstream_owner"] == "acme"
    # PR body ссылается на ЦЕЛЕВОЙ issue + bounty источник
    assert "acme/widgets/issues/52328" in kw["pr_body"]
    assert "bounty: https://github.com/zhang/bounty-plaza/issues/802" in kw["pr_body"]


def test_v218_explicit_paths_priority():
    eng = BountySolutionEngine(balancer=FakeBalancer(), pr_builder=FakeBuilderV3())
    r = eng.solve_and_pr(BOUNTY_PLATFORM, dry_run=True)
    # engine.cpp упомянут в issue явно — обязан попасть в контекст первым
    assert r["context_files"] and r["context_files"][0] == "src/widgets/engine.cpp"  # приоритет explicit


def test_v218_retry_after_marker_failure():
    class FlakyBalancer:
        def __init__(self):
            self.n = 0

        def chat(self, messages, task_type="general"):
            self.n += 1
            return "много прозы без маркеров" if self.n == 1 else CANNED

    bal = FlakyBalancer()
    b = FakeBuilder()
    eng = BountySolutionEngine(balancer=bal, pr_builder=b)
    r = eng.solve_and_pr(BOUNTY, dry_run=True)
    assert r["status"] == "dry_run"
    assert bal.n == 2  # retry сработал


def test_v218_no_cross_repo_link_keeps_host():
    eng = BountySolutionEngine(balancer=FakeBalancer(), pr_builder=FakeBuilderV2())
    r = eng.solve_and_pr(BOUNTY_P, dry_run=True)
    assert r["target_repo"] == "owner/repo"


# ---------------- v21.8b: относительные пути + same-dir boost ----------------

MSDA_TREE = {"tree": [
    {"path": "ttnn/cpp/ttnn/operations/experimental/multi_scale_deformable_attn/device/multi_scale_deformable_attn_device_operation.cpp", "type": "blob"},
    {"path": "ttnn/cpp/ttnn/operations/experimental/multi_scale_deformable_attn/device/kernels/dataflow/reader_msda.cpp", "type": "blob"},
    {"path": "ttnn/cpp/ttnn/operations/experimental/multi_scale_deformable_attn/device/kernels/dataflow/writer_msda.cpp", "type": "blob"},
    {"path": "models/experimental/gated_attention/tests/test_ttnn_attention.py", "type": "blob"},
    {"path": "README.md", "type": "blob"},
]}

BOUNTY_REL = {
    "id": "gh_r1", "number": 52328,
    "title": "Generalize multi_scale_deformable_attn D",
    "body": ("`ttnn/cpp/ttnn/operations/experimental/multi_scale_deformable_attn/device/"
             "multi_scale_deformable_attn_device_operation.cpp:68-74` требует D=32.\n"
             "Also check device/kernels/dataflow/reader_msda.cpp for HALF_STICK_NBYTES."),
    "html_url": "https://github.com/acme/tt-metal/issues/52328",
    "repository_url": "https://api.github.com/repos/acme/tt-metal",
}


class FakeBuilderV4(FakeBuilder):
    """Гигантский репо acme/tt-metal; записывает запрошенные contents-пути."""

    def __init__(self):
        super().__init__()
        self.requested = []

    def gh(self, method, path, payload=None, timeout=20):
        if path.startswith("/repos/acme/tt-metal/git/trees"):
            return dict(MSDA_TREE), None
        if path.startswith("/repos/acme/tt-metal/contents?"):
            return [{"path": "ttnn", "type": "dir"}, {"path": "README.md", "type": "file"}], None
        if path.startswith("/repos/acme/tt-metal/contents/") and "ref=" in path:
            fname = path.split("contents/")[1].split("?")[0]
            self.requested.append(fname)
            return {"encoding": "base64",
                    "content": base64.b64encode(f"// {fname}\n".encode()).decode()}, None
        if path.startswith("/repos/acme/tt-metal"):
            return {"default_branch": "main"}, None
        return super().gh(method, path, payload, timeout)


def test_v218b_relative_explicit_resolved():
    b = FakeBuilderV4()
    eng = BountySolutionEngine(balancer=FakeBalancer(), pr_builder=b)
    r = eng.solve_and_pr(BOUNTY_REL, dry_run=True)
    assert r["status"] == "dry_run"
    assert r["context_files"]
    # ВСЕ контекстные файлы — полные пути из дерева, никаких относительных device/...
    # относительный путь из issue зарезолвлен в полный (никаких device/... запросов)
    assert not any(pf.startswith("device/") for pf in b.requested), b.requested
    assert any("reader_msda.cpp" in pf for pf in b.requested)


def test_v218b_same_dir_boost():
    from aios_core.bounty_solution_engine import _same_dir_boost, _score_path, _issue_tokens
    explicit = ["ttnn/cpp/ttnn/operations/experimental/multi_scale_deformable_attn/device/multi_scale_deformable_attn_device_operation.cpp"]
    writer = "ttnn/cpp/ttnn/operations/experimental/multi_scale_deformable_attn/device/kernels/dataflow/writer_msda.cpp"
    noise = "models/experimental/gated_attention/tests/test_ttnn_attention.py"
    assert _same_dir_boost(writer, explicit) >= 6
    assert _same_dir_boost(noise, explicit) == 0
    tokens = _issue_tokens(BOUNTY_REL)
    assert _score_path(writer, tokens) + _same_dir_boost(writer, explicit) > (
        _score_path(noise, tokens) + _same_dir_boost(noise, explicit))


def test_v218c_unknown_explicit_kept_for_fetch_verification():
    """Путь не найден в усечённом дереве, но contents API его подтверждает → в контекст."""
    bty = dict(BOUNTY_REL, body="Fix src/unknown/hidden_module.cpp please, D=64 crash")
    b = FakeBuilderV4()
    eng = BountySolutionEngine(balancer=FakeBalancer(), pr_builder=b)
    r = eng.solve_and_pr(bty, dry_run=True)
    assert r["status"] == "dry_run"
    assert "src/unknown/hidden_module.cpp" in b.requested
