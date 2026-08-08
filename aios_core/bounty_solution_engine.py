"""AIOS Bounty Solution Engine — v21.8.

Связка «issue → LLM-план правок → реальный PR» поверх BountyPRBuilder.

  1. Контекст репозитория: default_branch + корневое дерево файлов (REST)
  2. v21.7: рекурсивное дерево → скоринг релевантных файлов → их ИСХОДНЫЙ
     КОД попадает в промпт (LLM больше не гадает по именам файлов)
  3. v21.8: резолв целевого репо из bounty-платформ (bounty-plaza/алгора
     issue == описание, КОД в другом репо по Source URL); явные пути файлов
     из тела issue (`path/file.cpp:68-74`) — гарантированные слоты контекста;
     retry со строгим напоминанием при провале маркер-парса
  4. LLM: issue title/body + дерево + код → маркерный формат file_changes
  5. Гейты качества: ≤3 файлов, без .git/workflows, ≤15k символов/файл
  6. BountyPRBuilder.build_pr() — dry-run по умолчанию (AIOS_BOUNTY_PR=plan|live)

Ветка детерминирована: aios/bounty-<num> → повторный прогон даёт
already_exists (политика «1 PR на баунти»), новых исправлений можно
добавлять коммитами в ту же ветку позже.
"""
from __future__ import annotations

import base64
import json
import logging
import os
import re
from typing import Any, Dict, List, Optional, Tuple

from aios_core.bounty_pr_builder import BountyPRBuilder, SAFE_PATH_RE
from aios_core.llm_balancer import LLMBalancer

logger = logging.getLogger("AIOS.BountySolutionEngine")

BANNED_PREFIXES = (".git", ".github/workflows", "node_modules", "vendor", "dist")
MAX_FILES = 3
MAX_FILE_CHARS = 15000
MAX_TOTAL_CHARS = 30000

# v21.7: полный файловый контекст для планов
MAX_TREE_PATHS = int(os.environ.get("AIOS_BOUNTY_PR_MAX_TREE_PATHS", "25000"))
# tt-metal-класс репо: ~25k файлов; меньший срез затирает целевые поддеревья
CONTEXT_MAX_BYTES = int(os.environ.get("AIOS_BOUNTY_PR_CONTEXT_BYTES", "20000"))
PER_FILE_CONTEXT_BYTES = 7000
CONTEXT_FILES = int(os.environ.get("AIOS_BOUNTY_PR_CONTEXT_FILES", "5"))

_SOURCE_EXTS = (".py", ".js", ".ts", ".tsx", ".jsx", ".go", ".rs", ".cpp", ".cc",
                ".cxx", ".h", ".hpp", ".c", ".java", ".kt", ".rb", ".php",
                ".cs", ".cu", ".cuh", ".scala", ".swift", ".m", ".sol")
_DOC_EXTS = (".md", ".rst", ".txt", ".png", ".jpg", ".jpeg", ".svg", ".lock",
             ".gif", ".pdf", ".ico", ".csv")
_SKIP_TOKENS = {"the", "and", "for", "with", "from", "this", "that", "when",
                "issue", "error", "bug", "fix", "add", "new", "use", "not",
                "you", "your", "are", "was", "were", "have", "has", "been",
                "please", "would", "could", "should", "what", "how", "why"}

# v21.8: ссылки на целевой репо/issue в описании баунти-платформы
TARGET_ISSUE_RE = re.compile(
    r"github\.com/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)/(?:issues|pull)/(\d+)")
# явные пути файлов в тексте issue: `ttnn/cpp/.../file.cpp:68-74` и т.п.
_EXPLICIT_PATH_RE = re.compile(
    r"(?<![\w/.-])((?:[\w.+-]+/)+[\w.+-]+\.(?:py|js|ts|tsx|jsx|go|rs|cpp|cc|cxx|"
    r"c|h|hpp|cu|cuh|java|kt|rb|php|cs|scala|swift|m|sol|json|ya?ml|toml|cfg|ini))"
    r"(?::\d+(?:-\d+)?)?")

_STRICT_REMINDER = (
    "\n\nВАЖНО: предыдущий твой ответ НЕ прошёл парсер. Ответь СТРОГО маркерами "
    "PR_TITLE:/PR_BODY:/FILE:/<<CONTENT>>/<<END_FILE>>/ANALYSIS: — без прозы, "
    "без markdown-обёрток вокруг имён маркеров.\n")


def _issue_tokens(bounty: Dict[str, Any]) -> List[str]:
    text = f"{bounty.get('title', '')} {(bounty.get('body') or '')[:2000]}"
    toks = re.findall(r"[A-Za-z][A-Za-z0-9_]{2,}", text.lower())
    return sorted({t for t in toks if t not in _SKIP_TOKENS})


def _explicit_paths(bounty: Dict[str, Any]) -> List[str]:
    """Пути файлов, дословно упомянутые в issue (с опц. :строками). До 5."""
    text = f"{bounty.get('title', '')}\n{bounty.get('body') or ''}"
    out: List[str] = []
    for m in _EXPLICIT_PATH_RE.finditer(text):
        p = m.group(1)
        if p.count("/") < 1 or p.startswith((".git", "http")):
            continue
        if p not in out:
            out.append(p)
    return out[:5]


def _same_dir_boost(path: str, explicit: List[str]) -> int:
    """Сколько ведущих сегментов директории совпало с explicit-путём (>=2 → буст).
    Файлы рядом с упомянутым в issue файлом обычно и есть цель правки."""
    best = 0
    pparts = path.split("/")[:-1]
    for e in explicit:
        eparts = e.split("/")[:-1]
        common = 0
        for a, b in zip(eparts, pparts):
            if a != b:
                break
            common += 1
        best = max(best, common)
    return best if best >= 2 else 0


def _score_path(path: str, tokens: List[str]) -> int:
    """Релевантность пути токенам issue: точное совпадение части пути +3,
    подстрока +1; буст исходникам и тестам, минус докам/бинарям."""
    p = path.lower()
    parts = set(re.split(r"[/._\-+]+", p))
    score = 0
    for t in tokens:
        if t in parts:
            score += 3
        elif t in p:
            score += 1
    if p.endswith(_SOURCE_EXTS):
        score += 1
    elif p.endswith(_DOC_EXTS):
        score -= 2
    if p.startswith(("test/", "tests/")) or "/tests/" in p or "/test_" in p:
        score += 1
    return score


class BountySolutionEngine:
    """LLM-генерация правок под конкретный issue + создание PR."""

    def __init__(self, balancer: Optional[Any] = None,
                 pr_builder: Optional[BountyPRBuilder] = None):
        self.balancer = balancer or LLMBalancer()
        self.builder = pr_builder or BountyPRBuilder()

    # ---------------- repo context ----------------
    def repo_meta(self, owner: str, repo: str) -> Tuple[Optional[str], List[str], Optional[str]]:
        """(default_branch, root_paths, error). Корневые пути — до 60 штук."""
        meta, err = self.builder.gh("GET", f"/repos/{owner}/{repo}")
        if err or not meta:
            return None, [], f"repo meta: {err}"
        branch = meta.get("default_branch") or "main"
        root, err = self.builder.gh("GET", f"/repos/{owner}/{repo}/contents?per_page=100")
        paths: List[str] = []
        if isinstance(root, list):
            for it in root[:60]:
                p = it.get("path") or ""
                t = it.get("type") or ""
                paths.append(p + ("/" if t == "dir" else ""))
        return branch, paths, None

    # ---------------- v21.7: полный файловый контекст ----------------
    def repo_tree(self, owner: str, repo: str, branch: str) -> List[str]:
        """Рекурсивное дерево blob-путей одним REST-вызовом, capped MAX_TREE_PATHS."""
        data, err = self.builder.gh(
            "GET", f"/repos/{owner}/{repo}/git/trees/{branch}?recursive=1")
        if err or not isinstance(data, dict):
            logger.warning("repo_tree %s/%s: %s", owner, repo, err)
            return []
        paths = [e.get("path", "") for e in data.get("tree", [])
                 if e.get("type") == "blob" and e.get("path")]
        return paths[:MAX_TREE_PATHS]

    def select_relevant_files(self, bounty: Dict[str, Any], paths: List[str],
                              max_files: int = CONTEXT_FILES,
                              explicit: Optional[List[str]] = None) -> List[str]:
        """Топ-N файлов по скорингу токенов issue (+буст соседям explicit-путей)."""
        tokens = _issue_tokens(bounty)
        ex = explicit or []
        scored = sorted(
            ((p, _score_path(p, tokens) + _same_dir_boost(p, ex))
             for p in paths if p and not p.endswith("/")),
            key=lambda x: (-x[1], len(x[0])))
        return [p for p, s in scored if s > 0][:max_files]

    def fetch_context(self, owner: str, repo: str, branch: str,
                      files: List[str]) -> Dict[str, str]:
        """Содержимое файлов через contents API (base64). Бюджет CONTEXT_MAX_BYTES."""
        ctx: Dict[str, str] = {}
        budget = CONTEXT_MAX_BYTES
        for path in files:
            if budget <= 0:
                break
            data, err = self.builder.gh(
                "GET", f"/repos/{owner}/{repo}/contents/{path}?ref={branch}")
            if err or not isinstance(data, dict) or data.get("encoding") != "base64":
                continue
            try:
                text = base64.b64decode(data.get("content") or b"").decode("utf-8", "replace")
            except Exception:
                continue
            text = text[:PER_FILE_CONTEXT_BYTES]
            if len(text) > budget:
                text = text[:budget]
            if text.strip():
                ctx[path] = text
                budget -= len(text)
        return ctx

    # ---------------- v21.8: резолв целевого репо ----------------
    def resolve_target(self, bounty: Dict[str, Any], owner: str, repo: str
                       ) -> Tuple[str, str, Dict[str, Any]]:
        """Bounty-платформы (bounty-plaza и пр.) публикуют ОПИСАНИЕ, а код лежит
        в upstream-репо по ссылке вида github.com/org/repo/issues/NN (Source URL).
        Возвращает (owner, repo, bounty) целевого issue; при отсутствии ссылки
        или ошибке фетча — исходную тройку."""
        body = bounty.get("body") or ""
        m = TARGET_ISSUE_RE.search(body)
        if not m:
            return owner, repo, bounty
        to, trepo, inum = m.group(1), m.group(2), m.group(3)
        if f"{to}/{trepo}".lower() == f"{owner}/{repo}".lower():
            return owner, repo, bounty
        issue, err = self.builder.gh("GET", f"/repos/{to}/{trepo}/issues/{inum}")
        if (err or not isinstance(issue, dict) or not issue.get("title")
                or issue.get("pull_request")):
            logger.warning("resolve target %s/%s#%s failed: %s", to, trepo, inum, err)
            return owner, repo, bounty
        merged = dict(bounty)
        merged.update({
            "title": issue.get("title") or bounty.get("title"),
            "body": issue.get("body") or bounty.get("body"),
            "repository_url": f"https://api.github.com/repos/{to}/{trepo}",
            "html_url": issue.get("html_url") or bounty.get("html_url"),
            "bounty_source_url": bounty.get("html_url"),
            "target_issue_number": int(inum),
        })
        logger.info("🎯 целевой репозиторий: %s/%s issue #%s (host %s/%s #%s)",
                    to, trepo, inum, owner, repo, bounty.get("number"))
        return to, trepo, merged

    # ---------------- v21.9: гейт конкуренции ----------------
    def competition_check(self, owner: str, repo: str, issue_num: int) -> Dict[str, Any]:
        """Не тратим LLM/PR на гонки, где уже проиграли:
        issue закрыт / назначен чужой assignee / есть открытый чужой PR /
        issue закрыт мёрджем чужого PR. Мягкий ok при ошибках фетча."""
        issue, err = self.builder.gh("GET", f"/repos/{owner}/{repo}/issues/{issue_num}")
        if err or not isinstance(issue, dict):
            return {"status": "ok", "note": f"issue fetch failed: {err}"}
        if issue.get("pull_request"):
            return {"status": "skip", "reason": "цель — PR, а не issue"}
        if (issue.get("state") or "open") != "open":
            return {"status": "skip", "reason": f"issue #{issue_num} {issue.get('state')}"}
        me = ""
        try:
            me = self.builder.me() or ""
        except Exception:
            pass
        assignees = [a.get("login") for a in issue.get("assignees", []) if a.get("login")]
        if any(a != me for a in assignees):
            return {"status": "skip", "reason": f"assignee: {assignees}"}
        tl, err = self.builder.gh(
            "GET", f"/repos/{owner}/{repo}/issues/{issue_num}/timeline?per_page=100")
        pr_nums: List[int] = []
        if isinstance(tl, list):
            for ev in tl:
                if ev.get("event") != "cross-referenced":
                    continue
                src = (ev.get("source") or {}).get("issue") or {}
                if src.get("pull_request") and src.get("number"):
                    if int(src["number"]) not in pr_nums:
                        pr_nums.append(int(src["number"]))
        for n in pr_nums[:5]:
            pr, _ = self.builder.gh("GET", f"/repos/{owner}/{repo}/pulls/{n}")
            if not isinstance(pr, dict):
                continue
            author = (pr.get("user") or {}).get("login") or ""
            if author and author == me:
                continue  # наш PR — builder сам вернёт already_exists
            if pr.get("merged_at"):
                return {"status": "skip",
                        "reason": f"закрыт мёрджем чужого PR #{n} (@{author})",
                        "merged_pr": n}
            if (pr.get("state") or "") == "open":
                return {"status": "skip",
                        "reason": f"конкуренция: открыт PR #{n} (@{author})",
                        "competing_pr": n}
        return {"status": "ok"}

    def gate_for_bounty(self, bounty: Dict[str, Any]) -> Dict[str, Any]:
        """v21.10: resolve_target + competition_check БЕЗ LLM — радар свежих баунти.
        Мягкий ok при любых ошибках фетча."""
        repo_url = str(bounty.get("repository_url") or "")
        m = re.search(r"repos/([^/]+)/([^/]+)$", repo_url)
        if not m:
            m = re.search(r"github\.com/([^/]+)/([^/]+)/(?:issues|pull)/\d+",
                          str(bounty.get("html_url") or ""))
        if not m:
            return {"status": "ok", "note": "repo parse failed"}
        owner, repo = m.group(1), m.group(2)
        try:
            owner, repo, merged = self.resolve_target(bounty, owner, repo)
            num = int(merged.get("target_issue_number") or merged.get("number"))
        except Exception as e:
            return {"status": "ok", "note": f"resolve failed: {str(e)[:60]}"}
        gate = self.competition_check(owner, repo, num)
        gate["target_repo"] = f"{owner}/{repo}"
        gate["issue_num"] = num
        return gate

    def repo_quality(self, owner: str, repo: str) -> Dict[str, Any]:
        """v21.12: метрики качества репо для радара (звёзды, архивность, активность)."""
        meta, err = self.builder.gh("GET", f"/repos/{owner}/{repo}")
        if err or not isinstance(meta, dict):
            return {"stars": None, "archived": None, "note": f"meta failed: {str(err)[:60]}"}
        return {"stars": meta.get("stargazers_count", 0),
                "forks": meta.get("forks_count", 0),
                "archived": bool(meta.get("archived")),
                "pushed_at": meta.get("pushed_at"),
                "language": meta.get("language")}

    # ---------------- LLM plan ----------------
    def plan_file_changes(self, bounty: Dict[str, Any], root_paths: List[str],
                          file_context: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """LLM → маркерный формат (устойчив к сырому коду в content) + гейты путей/объёмов.

        JSON раньше ломался: LLM пишет многострочный код без экранирования
        -> invalid JSON гарантированно. Маркеры парсятся регэкспами надёжно.
        v21.7: file_context — реальный код релевантных файлов в промпте.
        v21.8: retry со строгим напоминанием при провале маркер-парса.
        """
        tree_hint = "\n".join(root_paths[:50])

        ctx_section = ""
        if file_context:
            blocks = [f"### {p}\n```\n{c.rstrip()}\n```" for p, c in file_context.items()]
            ctx_section = ("\n\nИСХОДНЫЙ КОД РЕЛЕВАНТНЫХ ФАЙЛОВ (может быть усечён):\n"
                           + "\n\n".join(blocks))

        ctx_rules = (""
                     if not file_context else
                     "\n- ИСХОДНЫЙ КОД приведён — базируй CONTENT СТРОГО на нём: сохраняй "
                     "существующие функции/классы/стиль, вноси точечные изменения под issue, "
                     "файл верни ЦЕЛИКОМ (не фрагмент).")

        prompt = f"""Ты — старший инженер AIOS, решающий GitHub bounty issue реальным Pull Request.

РЕПОЗИТОРИЙ (корневые пути):
{tree_hint}
{ctx_section}

ISSUE: {bounty.get('title', '')}
ОПИСАНИЕ: {(bounty.get('body') or '')[:1500]}

ОТВЕТЬ СТРОГО В МАРКЕРНОМ ФОРМАТЕ (никакого JSON и пояснений вне маркеров):

PR_TITLE: fix: краткий заголовок PR до 80 символов
PR_BODY:
## Что сделано
...
## Как проверено
...
FILE: путь/файла.py
REASON: зачем этот файл
<<CONTENT>>
(полный новый контент файла построчно)
<<END_FILE>>
ANALYSIS: 2-3 предложения сути проблемы и подхода

ПРАВИЛА:
- 1..{MAX_FILES} блока FILE МАКСИМУМ, только осмысленные правки под issue.
- В CONTENT — ПОЛНЫЙ контент файла после правки (не diff); маркер <<END_FILE>> внутри контента запрещён.
- Запрещены пути: .git, .github/workflows, node_modules, vendor, dist.{ctx_rules}
- Если код-правок предложить нельзя (мало контекста) — сделай новый файл
  docs/IMPLEMENTATION_PLAN.md с конкретным пошаговым планом решения ЭТОГО issue.
"""
        raw = ""
        title_m = body_m = analysis_m = None
        file_blocks: List[tuple] = []
        for attempt in range(2):
            p = prompt if attempt == 0 else prompt + _STRICT_REMINDER
            raw = self.balancer.chat([{"role": "user", "content": p}], task_type="code")
            # groq/llama любит оборачивать маркеры в markdown-«болд»: **FILE:** -> FILE:
            raw = re.sub(r"\*\*(PR_TITLE|PR_BODY|FILE|REASON|ANALYSIS):\*\*", r"\1:", raw)

            title_m = re.search(r"^PR_TITLE:\s*(.+?)\s*$", raw, re.M)
            body_m = re.search(r"PR_BODY:\s*(.*?)(?=^FILE:|^ANALYSIS:|\Z)", raw, re.M | re.S)
            analysis_m = re.search(r"^ANALYSIS:\s*(.+?)\s*$", raw, re.M | re.S)

            # FILE-блоки: контент либо в <<CONTENT>>...<<END_FILE>>, либо в ```фенсе```
            parts = re.split(r"(?m)^(FILE:\s*\S+.*)$", raw)
            file_blocks = []
            for i in range(1, len(parts) - 1, 2):
                head, seg = parts[i], parts[i + 1]
                path = head.split(":", 1)[1].strip().strip("`")
                cm = re.search(r"<<CONTENT>>\s*\n?(.*?)(?:^<<END_FILE>>|\Z)", seg, re.S | re.M)
                content = (cm.group(1) if cm else "").rstrip("\n")
                if not content.strip():
                    fm = re.search(r"```[a-zA-Z#+]*\n(.*?)```", seg, re.S)
                    content = (fm.group(1) if fm else "").rstrip("\n")
                # обрубаем хвостовой висячий фенс, если LLM не закрыл его сам
                content = re.sub(r"\n```\s*$", "", content)
                file_blocks.append((path, content))

            if title_m or file_blocks:
                break
            logger.warning("marker parse failed, попытка %d/2", attempt + 1)

        if not title_m and not file_blocks:
            return {"status": "error", "error": "LLM marker parse failed (no PR_TITLE/FILE)"}

        changes: Dict[str, str] = {}
        skipped: List[str] = []
        total = 0
        for path, content in file_blocks[:MAX_FILES + 2]:
            if len(changes) >= MAX_FILES:
                skipped.append(f"{path} (лимит файлов)")
                continue
            path = str(path).strip()
            content = content.rstrip("\n")
            if (not path or ".." in path or path.startswith("/")
                    or not SAFE_PATH_RE.match(path)
                    or any(path.lower().startswith(bp) for bp in BANNED_PREFIXES)):
                skipped.append(f"{path or '?'} (unsafe/banned)")
                continue
            if "<<END_FILE>>" in content or not content.strip():
                skipped.append(f"{path} (broken/empty)")
                continue
            content = content[:MAX_FILE_CHARS]
            if total + len(content) > MAX_TOTAL_CHARS:
                skipped.append(f"{path} (лимит объёма)")
                continue
            changes[path] = content
            total += len(content)

        if not changes:
            return {"status": "error", "error": f"all files rejected: {skipped}"}

        pr_title = ((title_m.group(1) if title_m else "")
                    or f"fix: {bounty.get('title', '')[:60]}")[:100]
        pr_body = (body_m.group(1).strip() if body_m else "") or \
                  (analysis_m.group(1) if analysis_m else "")
        src_note = ""
        if bounty.get("bounty_source_url"):
            src_note = f" (bounty: {bounty['bounty_source_url']})"
        pr_body = (pr_body[:4000]
                   + f"\n\n---\n🤖 Сгенерировано AIOS Bounty Engine (issue: "
                     f"{bounty.get('html_url', '')}){src_note}")
        return {
            "status": "ok",
            "changes": changes,
            "pr_title": pr_title,
            "pr_body": pr_body,
            "analysis": (analysis_m.group(1) if analysis_m else "")[:500],
            "skipped": skipped,
            "total_chars": total,
        }

    # ---------------- main ----------------
    def solve_and_pr(self, bounty: Dict[str, Any], dry_run: bool = True) -> Dict[str, Any]:
        repo_url = str(bounty.get("repository_url") or "")
        m = re.search(r"repos/([^/]+)/([^/]+)$", repo_url)
        if not m:
            m = re.search(r"github\.com/([^/]+)/([^/]+)/(?:issues|pull)/\d+", str(bounty.get("html_url") or ""))
        if not m:
            return {"status": "error", "error": "cannot parse owner/repo"}
        owner, repo = m.group(1), m.group(2)

        # v21.8: bounty-платформа? идём в целевой репозиторий кода
        owner, repo, bounty = self.resolve_target(bounty, owner, repo)

        # v21.9: гейт конкуренции ДО траты LLM-токенов
        try:
            issue_num = int(bounty.get("target_issue_number") or bounty.get("number"))
        except (TypeError, ValueError):
            issue_num = None
        if issue_num:
            gate_res = self.competition_check(owner, repo, issue_num)
            if gate_res.get("status") == "skip":
                logger.info("⏭️ гейт конкуренции #%s: %s", issue_num, gate_res.get("reason"))
                out = {"status": "skipped", "reason": gate_res.get("reason"),
                       "target_repo": f"{owner}/{repo}", "branch": f"aios/bounty-{issue_num}"}
                for k in ("merged_pr", "competing_pr"):
                    if k in gate_res:
                        out[k] = gate_res[k]
                return out

        branch_base, root_paths, err = self.repo_meta(owner, repo)
        if err:
            return {"status": "error", "error": err}

        # v21.7: рекурсивное дерево → релевантные файлы → их код в контекст
        tree_paths = self.repo_tree(owner, repo, branch_base or "main")
        # v21.8: явные пути из тела issue — гарантированные слоты контекста
        explicit = _explicit_paths(bounty)
        if explicit and tree_paths:
            known = set(tree_paths)
            # дерево может быть усечено гигантским репо → contents API проверит путь
            resolved: List[str] = []
            for ep in explicit:
                if ep in known:
                    resolved.append(ep)
                    continue
                # issue цитирует путь относительно модуля → ищем суффикс в дереве
                cand = [t for t in tree_paths if t.endswith("/" + ep)]
                resolved.append(sorted(cand, key=len)[0] if cand else ep)
            explicit = list(dict.fromkeys(resolved))
        scored_sel = self.select_relevant_files(bounty, tree_paths or root_paths,
                                                explicit=explicit)
        context_files: List[str] = []
        for p in explicit[:3] + scored_sel:
            if p not in context_files:
                context_files.append(p)
        context_files = context_files[:CONTEXT_FILES + 2]
        file_context = self.fetch_context(owner, repo, branch_base or "main", context_files)
        if context_files:
            logger.info("📎 контекст для баунти #%s: %s (%d байт)",
                        bounty.get("number"), context_files,
                        sum(len(v) for v in file_context.values()))

        plan = self.plan_file_changes(bounty, root_paths, file_context=file_context)
        if plan["status"] != "ok":
            return plan

        num = bounty.get("number") or abs(hash(str(bounty.get("html_url") or bounty.get("id")))) % 100000
        branch = f"aios/bounty-{num}"

        r = self.builder.build_pr(
            upstream_owner=owner, repo=repo, base_branch=branch_base or "main",
            file_changes=plan["changes"], branch_name=branch,
            pr_title=plan["pr_title"], pr_body=plan["pr_body"])
        return {
            "status": r.get("status"),
            "url": r.get("url"),
            "number": r.get("number"),
            "branch": branch,
            "dry_run": dry_run or self.builder.dry_run,
            "target_repo": f"{owner}/{repo}",
            "files": sorted(plan["changes"]),
            "context_files": context_files,
            "skipped": plan.get("skipped", []),
            "analysis": plan.get("analysis"),
            "pr_steps": r.get("steps", []),
        }


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO)
    print(json.dumps({"module": "bounty_solution_engine",
                      "modes": {"AIOS_BOUNTY_PR": "off|plan|live"},
                      "status": "ready"}, ensure_ascii=False, indent=1))
