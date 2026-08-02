"""
Security Audit Module — проверка безопасности без ложных срабатываний.
"""
from __future__ import annotations
import re
import os
from pathlib import Path
from typing import List, Dict
import ast

class SecurityAuditor:
    def __init__(self, repo_path: str = "."):
        self.repo_path = Path(repo_path)
        self.exclude = {"__pycache__", ".git", "node_modules", "chroma_db", ".venv"}

    def audit_xss(self) -> List[Dict]:
        issues=[]
        for root, dirs, files in os.walk(self.repo_path):
            dirs[:] = [d for d in dirs if d not in self.exclude]
            for fname in files:
                if not fname.endswith(".py"):
                    continue
                fpath=Path(root)/fname
                if "test" in str(fpath):
                    continue
                try:
                    content=fpath.read_text(encoding="utf-8", errors="ignore")
                    # Look for raw html concatenation without escaping in NiceGUI/FastAPI
                    if "ui.html(" in content and "escape" not in content.lower():
                        # Check if user input directly passed
                        if "request" in content.lower() or "input" in content.lower():
                            issues.append({"file": str(fpath.relative_to(self.repo_path)), "type": "potential_xss", "desc": "ui.html with user input without escaping"})
                    if "innerHTML" in content or "dangerouslySetInnerHTML" in content:
                        issues.append({"file": str(fpath.relative_to(self.repo_path)), "type": "xss", "desc": "dangerous innerHTML"})
                except Exception:
                    continue
        return issues[:20]

    def audit_secrets(self) -> List[Dict]:
        patterns=[
            (r"sk-or-v1-[a-z0-9]+", "OpenRouter key"),
            (r"sk-proj-[A-Za-z0-9-_]+", "OpenAI key"),
            (r"ghp_[A-Za-z0-9_]{20,}", "GitHub token"),
        ]
        issues=[]
        for root, dirs, files in os.walk(self.repo_path):
            dirs[:] = [d for d in dirs if d not in self.exclude]
            for fname in files:
                if not fname.endswith(".py"):
                    continue
                fpath=Path(root)/fname
                rel=str(fpath.relative_to(self.repo_path))
                if "test" in rel or "example" in rel or ".bak" in rel:
                    continue
                try:
                    txt=fpath.read_text(encoding="utf-8", errors="ignore")
                    for pat, desc in patterns:
                        m=re.search(pat, txt)
                        if m:
                            # Skip if it's in env example or balancer
                            if "llm_balancer" in rel or "example" in rel:
                                continue
                            issues.append({"file": rel, "type": "secret", "desc": desc, "line": txt[:m.start()].count("\n")+1})
                            break
                except Exception:
                    continue
        return issues[:20]

    def audit_dangerous_calls(self) -> List[Dict]:
        issues=[]
        for root, dirs, files in os.walk(self.repo_path):
            dirs[:] = [d for d in dirs if d not in self.exclude]
            for fname in files:
                if not fname.endswith(".py"):
                    continue
                fpath=Path(root)/fname
                rel=str(fpath.relative_to(self.repo_path))
                if not rel.startswith("aios_core/"):
                    continue
                # Skip allowed files
                if rel in ("aios_core/llm_balancer.py", "aios_core/meta_cognitive_self_coder.py", "aios_core/tech_debt_reporter.py"):
                    continue
                try:
                    src=fpath.read_text(encoding="utf-8", errors="ignore")
                    tree=ast.parse(src)
                    for node in ast.walk(tree):
                        if isinstance(node, ast.Call):
                            if isinstance(node.func, ast.Name) and node.func.id in ("eval", "exec", "compile"):
                                issues.append({"file": rel, "type": "dangerous", "desc": f"{node.func.id}() at line {node.lineno}"})
                except Exception:
                    continue
        return issues[:20]

    def generate_report(self):
        return {
            "xss": self.audit_xss(),
            "secrets": self.audit_secrets(),
            "dangerous_calls": self.audit_dangerous_calls(),
        }

if __name__ == "__main__":
    import json
    aud=SecurityAuditor(".")
    rep=aud.generate_report()
    print(json.dumps(rep, indent=2, ensure_ascii=False))
