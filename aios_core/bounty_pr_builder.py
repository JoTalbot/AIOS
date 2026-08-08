"""AIOS Bounty PR Builder — v21.5 groundwork.

Режим реальных PR для GitHub-баунти (побеждают PR, не комментарии).
Целиком через REST GitHub API — без локального клона репозитория:
  fork → git/ref (ветка) → blobs → tree → commit → ref → PR.

Политика «ОДИН PR на баунти» (урок от мейнтейнера memanto/Xenogents):
  перед созданием ищем существующий open PR с нашей ветки — если есть,
  возвращаем его (already_exists), дубликаты никогда не создаём.

БЕЗОПАСНОСТЬ: dry-run по умолчанию. Live-записи только при
AIOS_BOUNTY_PR_MODE=1 в env/.env. В dry-run — ноль POST/PATCH/DELETE,
возвращается полный план шагов.

TODO(v21.6): интеграция в GitcoinAlgoraMasterSolver.run_bounty_cycle —
генерация file_changes из LLM-решения issue и вызов build_pr().
"""
from __future__ import annotations

import json
import logging
import os
import re
import time
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("AIOS.BountyPRBuilder")

DEFAULT_ENV_FILE = "/root/AIOS/.env"
SAFE_PATH_RE = re.compile(r"^[A-Za-z0-9_\-./]+$")
SAFE_BRANCH_RE = re.compile(r"^[A-Za-z0-9_\-/]+$")


def _load_token() -> str:
    tok = os.environ.get("GITHUB_API_KEY")
    if tok:
        return tok
    if os.path.exists(DEFAULT_ENV_FILE):
        for line in open(DEFAULT_ENV_FILE):
            if line.startswith("GITHUB_API_KEY="):
                return line.strip().split("=", 1)[1]
    raise RuntimeError("GITHUB_API_KEY not found")


class BountyPRBuilder:
    """Создание PR через REST API GitHub без локального клона."""

    def __init__(self, github_token: Optional[str] = None,
                 dry_run: Optional[bool] = None, api_base: str = "https://api.github.com"):
        self.token = github_token or _load_token()
        env_mode = os.environ.get("AIOS_BOUNTY_PR_MODE", "0").strip()
        self.dry_run = (env_mode != "1") if dry_run is None else dry_run
        self.api_base = api_base
        self._me: Optional[str] = None

    # ---------------- transport ----------------
    def gh(self, method: str, path: str, payload: Optional[dict] = None,
           timeout: int = 20) -> Tuple[Optional[Any], Optional[Any]]:
        """Returns (data, err). err = HTTPStatus/текст. Write-методы глушатся в dry-run."""
        if self.dry_run and method not in ("GET", "HEAD"):
            return None, "dry_run"
        url = path if path.startswith("http") else f"{self.api_base}{path}"
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode() if payload is not None else None,
            method=method,
            headers={
                "Authorization": f"token {self.token}",
                "User-Agent": "AIOS-BountyPRBuilder/1.0",
                "Accept": "application/vnd.github+json",
                "Content-Type": "application/json",
            })
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                body = r.read().decode()
                return json.loads(body) if body else {}, None
        except urllib.error.HTTPError as e:
            try:
                err_body = json.loads(e.read().decode() or "{}")
            except Exception:
                err_body = {}
            return None, {"status": e.code, "message": err_body.get("message", "")[:200]}
        except Exception as e:
            return None, {"status": 0, "message": str(e)[:200]}

    # ---------------- helpers ----------------
    @property
    def me(self) -> str:
        if not self._me:
            data, err = self.gh("GET", "/user")
            if err or not data:
                raise RuntimeError(f"/user failed: {err}")
            self._me = data["login"]
        return self._me

    def find_existing_pr(self, upstream_owner: str, repo: str, branch: str) -> Optional[str]:
        """URL открытого PR с нашей ветки в upstream, если уже есть (политика 1 PR/баунти)."""
        data, err = self.gh("GET",
            f"/repos/{upstream_owner}/{repo}/pulls?state=open&head={self.me}:{branch}")
        if err or not isinstance(data, list):
            return None
        for pr in data:
            head = pr.get("head") or {}
            if ((head.get("user") or {}).get("login") == self.me
                    and (head.get("ref") or "") == branch):
                return pr.get("html_url")
        return None

    def _ensure_fork(self, owner: str, repo: str, steps: List[str]) -> Dict[str, Any]:
        """Fork под токен-юзером есть → ок; нет → POST /forks и ждём готовности."""
        me = self.me
        fork, err = self.gh("GET", f"/repos/{me}/{repo}")
        if fork and not err:
            steps.append(f"fork exists: {me}/{repo}")
            return {"status": "ok"}
        steps.append(f"creating fork {owner}/{repo} -> {me}")
        _, err = self.gh("POST", f"/repos/{owner}/{repo}/forks")
        if err and not (isinstance(err, dict) and err.get("status") == 202):
            # 202 принимается тоже как ок (async fork creation); urllib отдаёт 2xx без ошибки
            return {"status": "error", "error": f"fork creation failed: {err}"}
        for _ in range(10):
            time.sleep(3)
            fork, err2 = self.gh("GET", f"/repos/{me}/{repo}")
            if fork and not err2:
                steps.append("fork ready")
                return {"status": "ok"}
        return {"status": "error", "error": "fork not ready after 30s"}

    # ---------------- main ----------------
    def build_pr(self, upstream_owner: str, repo: str, base_branch: str,
                 file_changes: Dict[str, str], branch_name: str,
                 pr_title: str, pr_body: str) -> Dict[str, Any]:
        """Один PR с набором правок файлов. dry_run=True → только план."""
        steps: List[str] = []
        # валидация
        if not file_changes:
            return {"status": "error", "error": "file_changes empty"}
        if not SAFE_BRANCH_RE.match(branch_name):
            return {"status": "error", "error": f"unsafe branch name: {branch_name!r}"}
        for path, content in file_changes.items():
            if not content.strip():
                return {"status": "error", "error": f"empty content: {path}"}
            if ".." in path or path.startswith("/") or not SAFE_PATH_RE.match(path):
                return {"status": "error", "error": f"unsafe path: {path!r}"}

        me = self.me
        plan_prefix = "[DRY-RUN] " if self.dry_run else ""

        # 0. политика: 1 PR на баунти
        existing = self.find_existing_pr(upstream_owner, repo, branch_name)
        if existing:
            steps.append(f"existing open PR found: {existing}")
            logger.info(f"{plan_prefix}skip: PR уже существует {existing}")
            return {"status": "already_exists", "url": existing, "branch": branch_name, "steps": steps}

        # 1. fork
        if self.dry_run:
            steps.append(f"ensure fork {me}/{repo} (GET /repos/{me}/{repo}, POST /forks if missing)")
        else:
            r = self._ensure_fork(upstream_owner, repo, steps)
            if r["status"] != "ok":
                return {**r, "steps": steps}

        steps_common = [
            f"GET base ref heads/{base_branch} @ {me}/{repo}",
            f"GET base commit -> tree sha",
            f"POST {len(file_changes)} blob(s): {sorted(file_changes)[:3]}{'...' if len(file_changes) > 3 else ''}",
            "POST tree (mode 100644)", "POST commit", f"PUT ref heads/{branch_name}",
            f"POST PR {upstream_owner}/{repo} base={base_branch} head={me}:{branch_name}",
        ]
        if self.dry_run:
            steps.extend(plan_prefix + s for s in steps_common)
            return {"status": "dry_run", "branch": branch_name,
                    "title": pr_title, "files": sorted(file_changes), "steps": steps,
                    "note": "AIOS_BOUNTY_PR_MODE=1 включит реальные записи"}

        # 2. base sha
        ref, err = self.gh("GET", f"/repos/{me}/{repo}/git/ref/heads/{base_branch}")
        if err or not ref:
            ref, err = self.gh("GET", f"/repos/{upstream_owner}/{repo}/git/ref/heads/{base_branch}")
        if err or not ref:
            return {"status": "error", "error": f"base ref: {err}", "steps": steps}
        base_sha = ref["object"]["sha"]
        steps.append(f"base {base_branch} @ {base_sha[:8]}")

        commit_obj, err = self.gh("GET", f"/repos/{me}/{repo}/git/commits/{base_sha}")
        if err or not commit_obj:
            commit_obj, err = self.gh("GET", f"/repos/{upstream_owner}/{repo}/git/commits/{base_sha}")
        if err or not commit_obj:
            return {"status": "error", "error": f"base commit: {err}", "steps": steps}
        base_tree_sha = commit_obj["tree"]["sha"]

        # 3. blobs
        tree_entries = []
        for path, content in file_changes.items():
            blob, err = self.gh("POST", f"/repos/{me}/{repo}/git/blobs",
                                {"content": content, "encoding": "utf-8"})
            if err or not blob:
                return {"status": "error", "error": f"blob {path}: {err}", "steps": steps}
            tree_entries.append({"path": path, "mode": "100644", "type": "blob",
                                 "sha": blob["sha"]})
        steps.append(f"{len(tree_entries)} blobs created")

        # 4. tree
        tree, err = self.gh("POST", f"/repos/{me}/{repo}/git/trees",
                            {"base_tree": base_tree_sha, "tree": tree_entries})
        if err or not tree:
            return {"status": "error", "error": f"tree: {err}", "steps": steps}

        # 5. commit
        msg = pr_title[:100]
        commit, err = self.gh("POST", f"/repos/{me}/{repo}/git/commits",
                              {"message": msg, "tree": tree["sha"], "parents": [base_sha]})
        if err or not commit:
            return {"status": "error", "error": f"commit: {err}", "steps": steps}
        steps.append(f"commit {commit['sha'][:8]}")

        # 6. ref
        ref_data, err = self.gh("POST", f"/repos/{me}/{repo}/git/refs",
                                {"ref": f"refs/heads/{branch_name}", "sha": commit["sha"]})
        if err:
            _, err2 = self.gh("PATCH", f"/repos/{me}/{repo}/git/refs/heads/{branch_name}",
                              {"sha": commit["sha"], "force": False})
            if err2:
                return {"status": "error", "error": f"ref: {err} / {err2}", "steps": steps}
        steps.append(f"branch {branch_name} pushed")

        # 7. PR
        pr, err = self.gh("POST", f"/repos/{upstream_owner}/{repo}/pulls",
                          {"title": pr_title, "head": f"{me}:{branch_name}",
                           "base": base_branch, "body": pr_body})
        if err:
            # 422 — PR уже существует (гонка): ищем и возвращаем
            existing2 = self.find_existing_pr(upstream_owner, repo, branch_name)
            if existing2:
                return {"status": "already_exists", "url": existing2,
                        "branch": branch_name, "steps": steps}
            return {"status": "error", "error": f"PR: {err}", "steps": steps}
        steps.append(f"PR created: {pr.get('html_url')}")
        logger.info(f"✅ [BountyPRBuilder] PR: {pr.get('html_url')}")
        return {"status": "created", "url": pr.get("html_url"),
                "number": pr.get("number"), "branch": branch_name, "steps": steps}


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO)
    print(json.dumps({
        "dry_run": BountyPRBuilder().dry_run,
        "hint": "AIOS_BOUNTY_PR_MODE=1 → live; пример в tests/test_v21_pr_mode.py",
    }, ensure_ascii=False, indent=1))
