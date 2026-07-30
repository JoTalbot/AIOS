"""
Meta-Cognitive Self-Coder (v3.0-LLM)
Autonomous code generation, refactoring, and self-healing via LLM + AST.

Features:
- LLM-powered code generation (OpenRouter / OpenAI-compatible API)
- AST-based security validation
- Git commit & push automation
- Self-healing pipeline (detect -> diagnose -> fix -> verify -> deploy)
- Telegram integration for reporting

Architecture:
    User/Bot -> MetaCognitiveCoder -> LLM API -> Code -> AST Validate -> Test -> Git Push
"""
from __future__ import annotations

import ast
import json
import logging
import os
import subprocess
import time
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

log = logging.getLogger("meta-coder")


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

@dataclass
class CoderConfig:
    """Configuration for MetaCognitiveCoder."""
    llm_api_key: str = ""
    llm_base_url: str = "https://openrouter.ai/api/v1"
    llm_model: str = "meta-llama/llama-4-maverick"
    repo_path: str = "/root/AIOS"
    max_tokens: int = 4096
    temperature: float = 0.2
    safety_check: bool = True
    auto_commit: bool = False
    auto_push: bool = False

    @classmethod
    def from_env(cls) -> CoderConfig:
        # In Docker the repository is mounted at /app; on the host this module
        # lives directly below the repository root. Never assume /root/AIOS.
        repo_default = str(Path(__file__).resolve().parents[1])
        return cls(
            llm_api_key=os.environ.get("OPENROUTER_API_KEY") or os.environ.get("LLM_API_KEY", ""),
            llm_base_url=os.environ.get("LLM_BASE_URL", "https://openrouter.ai/api/v1"),
            llm_model=os.environ.get("LLM_MODEL") or "mistralai/mistral-small-3.2-24b-instruct",
            repo_path=os.environ.get("AIOS_REPO_PATH") or repo_default,
            auto_commit=os.environ.get("AIOS_AUTO_COMMIT", "").lower() in ("1", "true"),
            auto_push=os.environ.get("AIOS_AUTO_PUSH", "").lower() in ("1", "true"),
        )


# ---------------------------------------------------------------------------
# LLM Client (zero-dependency, OpenAI-compatible)
# ---------------------------------------------------------------------------

class LLMClient:
    """Minimal OpenAI-compatible API client."""

    def __init__(self, config: CoderConfig):
        self.config = config

    def chat(self, messages: list[dict], system: str = "") -> str:
        """Send chat completion with multi-provider fallback."""
        all_messages = []
        if system:
            all_messages.append({"role": "system", "content": system})
        all_messages.extend(messages)

        # Build endpoint list. Runtime keys are stored outside the image in
        # /app/data/.llm_keys.json (or <repo>/data on the host).
        endpoints = []
        key_files = [Path("/app/data/.llm_keys.json"), Path(self.config.repo_path) / "data/.llm_keys.json"]
        seen_keys = set()
        for key_file in key_files:
            try:
                key_data = json.loads(key_file.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            for key in key_data.get("openrouter", []):
                if key and key not in seen_keys:
                    endpoints.append({
                        "url": "https://openrouter.ai/api/v1/chat/completions",
                        "key": key,
                        "model": "mistralai/mistral-small-3.2-24b-instruct",
                        "name": "OpenRouter",
                    })
                    seen_keys.add(key)

        gh_key = os.environ.get("GITHUB_API_KEY", "")
        if gh_key and gh_key not in seen_keys:
            endpoints.append({
                "url": "https://models.inference.ai.azure.com/chat/completions",
                "key": gh_key,
                "model": "gpt-4.1-mini",
                "name": "GitHub",
            })
            seen_keys.add(gh_key)
        if self.config.llm_api_key and self.config.llm_api_key not in seen_keys:
            endpoints.append({
                "url": self.config.llm_base_url.rstrip("/") + "/chat/completions",
                "key": self.config.llm_api_key,
                "model": self.config.llm_model,
                "name": "Config",
            })

        for ep in endpoints:
            try:
                payload = json.dumps({
                    "model": ep["model"],
                    "messages": all_messages,
                    "max_tokens": self.config.max_tokens,
                    "temperature": self.config.temperature,
                }).encode()
                req = urllib.request.Request(ep["url"], data=payload, headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {ep['key']}",
                })
                with urllib.request.urlopen(req, timeout=120) as resp:
                    data = json.loads(resp.read())
                if "choices" in data and data["choices"]:
                    return data["choices"][0]["message"]["content"]
            except Exception as e:
                log.warning(f"{ep['name']} failed: {e}")
                continue

        raise ValueError("Все LLM endpoints недоступны. Проверьте ключи и квоту провайдера.")




# ---------------------------------------------------------------------------
# AST Safety Validator
# ---------------------------------------------------------------------------

class SafetyValidator:
    """Validates generated code for safety using AST analysis."""

    DANGEROUS_IMPORTS = {"subprocess", "shutil"}
    DANGEROUS_CALLS = {"eval", "exec", "compile", "__import__", "getattr"}

    @classmethod
    def validate(cls, source: str) -> tuple[bool, list[str]]:
        """Check code for dangerous patterns. Returns (safe, warnings)."""
        warnings = []
        try:
            tree = ast.parse(source)
        except SyntaxError as e:
            return False, [f"SyntaxError: {e}"]

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name in cls.DANGEROUS_IMPORTS:
                        warnings.append(f"Warning: Dangerous import: {alias.name}")

            if isinstance(node, ast.ImportFrom):
                if node.module and node.module in cls.DANGEROUS_IMPORTS:
                    warnings.append(f"Warning: Dangerous import from: {node.module}")

            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id in cls.DANGEROUS_CALLS:
                    warnings.append(f"Forbidden call: {node.func.id}()")
                    return False, warnings

        safe = not any("Forbidden" in w for w in warnings)
        return safe, warnings


# ---------------------------------------------------------------------------
# AST Transformer (original v2.0 functionality preserved)
# ---------------------------------------------------------------------------

class SecurityDecoratorTransformer(ast.NodeTransformer):
    """AST-Transformer: injects @constitution_enforced into def run()."""

    def visit_FunctionDef(self, node):
        self.generic_visit(node)
        if node.name == "run":
            has_decorator = any(
                (isinstance(d, ast.Name) and d.id == "constitution_enforced") or
                (isinstance(d, ast.Call) and isinstance(d.func, ast.Name) and d.func.id == "constitution_enforced")
                for d in node.decorator_list
            )
            if not has_decorator:
                decorator = ast.Name(id="constitution_enforced", ctx=ast.Load())
                node.decorator_list.insert(0, decorator)
        return node


# ---------------------------------------------------------------------------
# Git Operations
# ---------------------------------------------------------------------------

class GitOps:
    """Git commit & push operations."""

    def __init__(self, repo_path: str):
        self.repo = repo_path

    def _run(self, *args) -> tuple[int, str]:
        try:
            result = subprocess.run(
                ["git"] + list(args),
                cwd=self.repo,
                capture_output=True,
                text=True,
                timeout=30,
            )
            return result.returncode, result.stdout + result.stderr
        except Exception as e:
            return 1, str(e)

    def status(self) -> str:
        _, out = self._run("status", "--short")
        return out.strip()

    def diff(self, file_path: str = "") -> str:
        args = ["diff"]
        if file_path:
            args.append(file_path)
        _, out = self._run(*args)
        return out.strip()

    def add_and_commit(self, files: list[str], message: str) -> tuple[bool, str]:
        for f in files:
            code, _ = self._run("add", f)
            if code != 0:
                return False, f"git add failed for {f}"

        code, out = self._run("commit", "-m", message)
        return code == 0, out

    def push(self, branch: str = "main") -> tuple[bool, str]:
        code, out = self._run("push", "origin", branch)
        return code == 0, out


# ---------------------------------------------------------------------------
# Code Change dataclass
# ---------------------------------------------------------------------------

@dataclass
class CodeChange:
    """Represents a single code change."""
    file_path: str
    old_code: str = ""
    new_code: str = ""
    description: str = ""
    safe: bool = True
    warnings: list[str] = field(default_factory=list)
    committed: bool = False
    pushed: bool = False
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


# ---------------------------------------------------------------------------
# MetaCognitiveCoder - Main Class
# ---------------------------------------------------------------------------

class MetaCognitiveCoder:
    """
    Autonomous code generation and refactoring agent (v3.0-LLM).

    Capabilities:
    1. generate_code() - LLM generates new Python module from description
    2. refactor_file() - LLM refactors existing file
    3. fix_bug() - LLM diagnoses and fixes a bug from traceback
    4. refactor_skill_ast() - AST-based security decorator injection (v2.0)
    5. review_code() - LLM reviews code and suggests improvements
    6. self_heal() - Full self-healing pipeline
    """

    SYSTEM_PROMPT = (
        "You are AIOS MetaCognitiveCoder, an autonomous coding agent. "
        "You write clean, well-documented Python 3.11+ code. "
        "Rules: "
        "- Always include type hints and docstrings "
        "- Follow PEP 8 "
        "- Use dataclasses where appropriate "
        "- Never use eval(), exec(), or __import__() "
        "- Always handle exceptions gracefully "
        "- Return ONLY the code in a python code block, no explanations outside "
        "- If asked to fix a bug, explain the root cause in a comment at the top"
    )

    def __init__(self, config: CoderConfig | None = None):
        self.version = "3.0-LLM"
        self.config = config or CoderConfig.from_env()
        self.llm = LLMClient(self.config)
        self.git = GitOps(self.config.repo_path)
        self.validator = SafetyValidator()
        self.history: list[CodeChange] = []

    # ---- Public API -------------------------------------------------------

    def generate_code(self, description: str, target_path: str = "") -> CodeChange:
        """Generate new Python module from natural language description."""
        log.info("Generating code: %s...", description[:80])

        prompt = (
            f"Generate a complete Python module based on this description:\n\n"
            f"{description}\n\n"
            f"Requirements:\n"
            f"- Target path: {target_path or 'new module'}\n"
            f"- Must be self-contained\n"
            f"- Include __all__ export list\n"
            f"- Include if __name__ == '__main__' block for testing\n"
        )
        response = self.llm.chat(
            [{"role": "user", "content": prompt}],
            system=self.SYSTEM_PROMPT,
        )

        code = self._extract_code(response)
        safe, warnings = self.validator.validate(code)

        change = CodeChange(
            file_path=target_path,
            new_code=code,
            description=description,
            safe=safe,
            warnings=warnings,
        )

        if target_path and safe:
            full_path = os.path.join(self.config.repo_path, target_path)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(code)
            log.info("Code written to %s", target_path)

        self.history.append(change)
        return change

    def refactor_file(self, file_path: str, instruction: str) -> CodeChange:
        """Refactor an existing file using LLM."""
        log.info("Refactoring %s: %s...", file_path, instruction[:80])

        full_path = os.path.join(self.config.repo_path, file_path)
        if not os.path.exists(full_path):
            return CodeChange(
                file_path=file_path,
                description=f"File not found: {file_path}",
                safe=False,
                warnings=["File does not exist"],
            )

        with open(full_path, "r", encoding="utf-8") as f:
            old_code = f.read()

        prompt = (
            f"Refactor this Python file according to the instruction.\n\n"
            f"INSTRUCTION: {instruction}\n\n"
            f"CURRENT CODE:\n```python\n{old_code}\n```\n\n"
            f"Return the complete refactored file. Preserve all existing functionality.\n"
        )
        response = self.llm.chat(
            [{"role": "user", "content": prompt}],
            system=self.SYSTEM_PROMPT,
        )

        new_code = self._extract_code(response)
        safe, warnings = self.validator.validate(new_code)

        change = CodeChange(
            file_path=file_path,
            old_code=old_code,
            new_code=new_code,
            description=instruction,
            safe=safe,
            warnings=warnings,
        )

        if safe:
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(new_code)
            log.info("Refactored: %s", file_path)

        self.history.append(change)
        return change

    def fix_bug(self, file_path: str, traceback_text: str) -> CodeChange:
        """Diagnose and fix a bug from traceback."""
        log.info("Fixing bug in %s...", file_path)

        full_path = os.path.join(self.config.repo_path, file_path)
        old_code = ""
        if os.path.exists(full_path):
            with open(full_path, "r", encoding="utf-8") as f:
                old_code = f.read()

        prompt = (
            f"Fix the bug in this Python file based on the traceback.\n\n"
            f"TRACEBACK:\n```\n{traceback_text}\n```\n\n"
            f"CURRENT CODE ({file_path}):\n```python\n{old_code}\n```\n\n"
            f"Requirements:\n"
            f"- Identify root cause\n"
            f"- Fix the bug\n"
            f"- Add error handling to prevent similar issues\n"
            f"- Return complete fixed file\n"
        )
        response = self.llm.chat(
            [{"role": "user", "content": prompt}],
            system=self.SYSTEM_PROMPT,
        )

        new_code = self._extract_code(response)
        safe, warnings = self.validator.validate(new_code)

        change = CodeChange(
            file_path=file_path,
            old_code=old_code,
            new_code=new_code,
            description=f"Bug fix: {traceback_text[:100]}",
            safe=safe,
            warnings=warnings,
        )

        if safe and new_code:
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(new_code)
            log.info("Bug fixed: %s", file_path)

        self.history.append(change)
        return change

    def review_code(self, file_path: str) -> str:
        """Review code and return improvement suggestions."""
        full_path = os.path.join(self.config.repo_path, file_path)
        if not os.path.exists(full_path):
            return f"File not found: {file_path}"

        with open(full_path, "r", encoding="utf-8") as f:
            code = f.read()

        prompt = (
            f"Review this Python code and provide:\n"
            f"1. Bugs or potential issues\n"
            f"2. Performance improvements\n"
            f"3. Readability improvements\n"
            f"4. Security concerns\n"
            f"5. Overall score (1-10)\n\n"
            f"```python\n{code}\n```\n"
        )
        return self.llm.chat(
            [{"role": "user", "content": prompt}],
            system="You are a senior Python code reviewer. Be concise and actionable.",
        )

    def refactor_skill_ast(self, file_path: str) -> bool:
        """AST-based security decorator injection (v2.0 legacy)."""
        log.info("[Meta-Coder] AST Analysis: %s", file_path)

        full_path = file_path if os.path.isabs(file_path) else os.path.join(self.config.repo_path, file_path)
        with open(full_path, "r", encoding="utf-8") as f:
            source = f.read()

        tree = ast.parse(source)
        transformer = SecurityDecoratorTransformer()
        new_tree = transformer.visit(tree)
        ast.fix_missing_locations(new_tree)
        new_source = ast.unparse(new_tree)

        if "constitution_enforced" not in source:
            new_source = "from aios_core.security import constitution_enforced\n\n" + new_source

        with open(full_path, "w", encoding="utf-8") as f:
            f.write(new_source)

        log.info("AST refactor complete: %s", file_path)
        return True

    # ---- Self-Healing Pipeline -------------------------------------------

    def self_heal(self, file_path: str, error_log: str) -> CodeChange:
        """Full self-healing: diagnose -> fix -> validate -> commit."""
        log.info("Self-healing pipeline: %s", file_path)

        change = self.fix_bug(file_path, error_log)

        if not change.safe:
            log.warning("Generated code failed safety check: %s", change.warnings)
            return change

        try:
            compile(change.new_code, file_path, "exec")
        except SyntaxError as e:
            change.warnings.append(f"Syntax error after fix: {e}")
            change.safe = False
            return change

        if self.config.auto_commit:
            ok, msg = self.git.add_and_commit(
                [file_path],
                f"auto-heal: {file_path} - {change.description[:60]}"
            )
            change.committed = ok
            if ok and self.config.auto_push:
                ok, msg = self.git.push()
                change.pushed = ok

        log.info("Self-healing complete: %s", file_path)
        return change

    # ---- Commit & Push ---------------------------------------------------

    def commit_change(self, change: CodeChange, message: str = "") -> bool:
        """Commit a code change to git."""
        msg = message or f"auto-code: {change.description[:60]}"
        ok, out = self.git.add_and_commit([change.file_path], msg)
        change.committed = ok
        return ok

    def push_changes(self) -> bool:
        """Push all committed changes to remote."""
        ok, out = self.git.push()
        return ok

    # ---- Status ----------------------------------------------------------

    def status(self) -> dict:
        """Return current status of the coder agent."""
        return {
            "version": self.version,
            "llm_model": self.config.llm_model,
            "llm_configured": bool(self.config.llm_api_key),
            "repo_path": self.config.repo_path,
            "git_status": self.git.status(),
            "changes_made": len(self.history),
            "auto_commit": self.config.auto_commit,
            "auto_push": self.config.auto_push,
        }

    # ---- Helpers ---------------------------------------------------------

    @staticmethod
    def _extract_code(response: str) -> str:
        if not response:
            return ""
        bt3 = chr(96) * 3
        bt3py = bt3 + "python"
        if bt3py in response:
            start = response.index(bt3py) + len(bt3py)
            try:
                end = response.index(bt3, start)
                return response[start:end].strip()
            except ValueError:
                return response[start:].strip()
        if bt3 in response:
            start = response.index(bt3) + 3
            try:
                end = response.index(bt3, start)
                return response[start:end].strip()
            except ValueError:
                return response[start:].strip()
        stripped = response.strip()
        if stripped.startswith(("import ", "from ", "def ", "class ", "\"\"\"", "#", "@")):
            return stripped
        return stripped
