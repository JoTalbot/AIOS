"""AIOS Bounty Solution Engine — v21.6.

Связка «issue → LLM-план правок → реальный PR» поверх BountyPRBuilder.

  1. Контекст репозитория: default_branch + корневое дерево файлов (REST)
  2. LLM: issue title/body + дерево → строгий JSON с file_changes
  3. Гейты качества: ≤3 файлов, без .git/workflows, ≤15k символов/файл
  4. BountyPRBuilder.build_pr() — dry-run по умолчанию (AIOS_BOUNTY_PR=plan|live)

Ветка детерминирована: aios/bounty-<num> → повторный прогон даёт
already_exists (политика «1 PR на баунти»), новых исправлений можно
добавлять коммитами в ту же ветку позже.
"""
from __future__ import annotations

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

    # ---------------- LLM plan ----------------
    def plan_file_changes(self, bounty: Dict[str, Any], root_paths: List[str]) -> Dict[str, Any]:
        """LLM → маркерный формат (устойчив к сырому коду в content) + гейты путей/объёмов.

        JSON раньше ломался: LLM пишет многострочный код без экранирования
        -> invalid JSON гарантированно. Маркеры парсятся регэкспами надёжно.
        """
        tree_hint = "\n".join(root_paths[:50])
        prompt = f"""Ты — старший инженер AIOS, решающий GitHub bounty issue реальным Pull Request.

РЕПОЗИТОРИЙ (корневые пути):
{tree_hint}

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
- Запрещены пути: .git, .github/workflows, node_modules, vendor, dist.
- Если код-правок предложить нельзя (мало контекста) — сделай новый файл
  docs/IMPLEMENTATION_PLAN.md с конкретным пошаговым планом решения ЭТОГО issue.
"""
        raw = self.balancer.chat([{"role": "user", "content": prompt}], task_type="code")
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
        pr_body = (body_m.group(1).strip() if body_m else "") or                   (analysis_m.group(1) if analysis_m else "")
        pr_body = pr_body[:4000] + f"\n\n---\n🤖 Сгенерировано AIOS Bounty Engine (issue: {bounty.get('html_url', '')})"
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

        branch_base, root_paths, err = self.repo_meta(owner, repo)
        if err:
            return {"status": "error", "error": err}

        plan = self.plan_file_changes(bounty, root_paths)
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
            "files": sorted(plan["changes"]),
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
