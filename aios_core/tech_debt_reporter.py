"""
Tech Debt Reporter — автоматический анализ технического долга.
Генерирует JSON отчет о TODO/FIXME/HACK, сложности, покрытии.

Используется авто-кодером для закрытия повторяющихся задач из бэклога.
"""
from __future__ import annotations
import os
import re
import json
import ast
from pathlib import Path
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import List, Dict, Any

@dataclass
class DebtItem:
    file: str
    line: int
    type: str  # TODO, FIXME, HACK, etc
    content: str
    severity: str = "medium"

@dataclass
class ComplexityItem:
    file: str
    function: str
    complexity: int
    lines: int

class TechDebtReporter:
    """Сканирует проект и генерирует отчет о техдолге."""
    
    PATTERNS = {
        "TODO": r"TODO[:\s]",
        "FIXME": r"FIXME[:\s]",
        "HACK": r"HACK[:\s]",
        "XXX": r"XXX[:\s]",
        "BUG": r"BUG[:\s]",
    }
    
    def __init__(self, repo_path: str = "."):
        self.repo_path = Path(repo_path)
        self.exclude_dirs = {"__pycache__", ".git", "node_modules", "chroma_db", ".venv", "backups", ".pytest_cache"}
    
    def scan_todos(self) -> List[DebtItem]:
        items = []
        for root, dirs, files in os.walk(self.repo_path):
            dirs[:] = [d for d in dirs if d not in self.exclude_dirs]
            for fname in files:
                if not fname.endswith(".py"):
                    continue
                fpath = Path(root) / fname
                rel = fpath.relative_to(self.repo_path)
                # Skip auto-coder internals
                if str(rel) in ("run_coder_orchestrator.py", "aios_core/llm_balancer.py", "aios_core/meta_cognitive_self_coder.py"):
                    continue
                try:
                    with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                        for i, line in enumerate(f, 1):
                            upper = line.upper()
                            for dtype, pat in self.PATTERNS.items():
                                if re.search(pat, upper):
                                    # skip string literals mentioning the tag
                                    if f'"{dtype}"' in upper or f"'{dtype}'" in upper:
                                        continue
                                    severity = "high" if dtype in ("FIXME", "BUG") else "medium" if dtype == "TODO" else "low"
                                    items.append(DebtItem(
                                        file=str(rel),
                                        line=i,
                                        type=dtype,
                                        content=line.strip()[:120],
                                        severity=severity
                                    ))
                                    break
                except Exception:
                    continue
                if len(items) > 200:
                    break
            if len(items) > 200:
                break
        return items
    
    def scan_complexity(self) -> List[ComplexityItem]:
        """Простой анализ сложности: считает ветвления в функциях."""
        complex_items = []
        for root, dirs, files in os.walk(self.repo_path):
            dirs[:] = [d for d in dirs if d not in self.exclude_dirs]
            for fname in files:
                if not fname.endswith(".py"):
                    continue
                fpath = Path(root) / fname
                rel = str(fpath.relative_to(self.repo_path))
                if not rel.startswith("aios_core/"):
                    continue
                try:
                    source = fpath.read_text(encoding="utf-8", errors="ignore")
                    tree = ast.parse(source)
                    for node in ast.walk(tree):
                        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                            # Count branches
                            branches = sum(1 for n in ast.walk(node) if isinstance(n, (ast.If, ast.For, ast.While, ast.Try, ast.With)))
                            lines = (node.end_lineno - node.lineno) if hasattr(node, 'end_lineno') else 0
                            if branches > 10 or lines > 100:
                                complex_items.append(ComplexityItem(
                                    file=rel,
                                    function=node.name,
                                    complexity=branches,
                                    lines=lines
                                ))
                except Exception:
                    continue
        return sorted(complex_items, key=lambda x: x.complexity, reverse=True)[:20]
    
    def scan_security(self) -> List[Dict[str, Any]]:
        """Базовый скан на hardcoded secrets и опасные вызовы."""
        issues = []
        secret_patterns = [
            (r"sk-[a-zA-Z0-9]{20,}", "potential OpenAI key"),
            (r"ghp_[a-zA-Z0-9]{20,}", "GitHub token"),
            (r"AKIA[0-9A-Z]{16}", "AWS key"),
            (r"password\s*=\s*['\"][^'\"]+['\"]", "hardcoded password"),
        ]
        for root, dirs, files in os.walk(self.repo_path):
            dirs[:] = [d for d in dirs if d not in self.exclude_dirs]
            for fname in files:
                if not fname.endswith((".py", ".env", ".yaml", ".yml")):
                    continue
                if "test" in fname or "example" in fname:
                    continue
                fpath = Path(root) / fname
                rel = str(fpath.relative_to(self.repo_path))
                try:
                    content = fpath.read_text(encoding="utf-8", errors="ignore")
                    for pat, desc in secret_patterns:
                        if re.search(pat, content, re.IGNORECASE):
                            # Skip if in .env.example or test
                            if ".example" in rel:
                                continue
                            issues.append({"file": rel, "type": "secret", "desc": desc})
                            break
                    # Check dangerous calls
                    if "eval(" in content or "exec(" in content:
                        if "eval(" in content and "self_heal" not in content:
                            issues.append({"file": rel, "type": "dangerous_call", "desc": "eval/exec usage"})
                except Exception:
                    continue
                if len(issues) > 50:
                    break
            if len(issues) > 50:
                break
        return issues

    def generate_report(self) -> Dict[str, Any]:
        todos = self.scan_todos()
        complexity = self.scan_complexity()
        security = self.scan_security()
        
        by_type = {}
        for item in todos:
            by_type[item.type] = by_type.get(item.type, 0) + 1
        
        report = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "summary": {
                "total_todos": len(todos),
                "by_type": by_type,
                "complex_functions": len(complexity),
                "security_issues": len(security),
            },
            "todos": [asdict(x) for x in todos[:100]],
            "complexity_hotspots": [asdict(x) for x in complexity],
            "security": security[:20],
            "recommendations": []
        }
        
        if by_type.get("FIXME", 0) > 5:
            report["recommendations"].append("Высокий уровень FIXME - требуется рефакторинг критичных модулей")
        if len(complexity) > 10:
            report["recommendations"].append(f"{len(complexity)} функций с высокой сложностью - разбить на мелкие")
        if security:
            report["recommendations"].append(f"Найдено {len(security)} потенциальных проблем безопасности")
        if by_type.get("TODO", 0) > 20:
            report["recommendations"].append("Много TODO - создать задачи в бэклоге для постепенного закрытия")
        
        return report
    
    def save_json(self, output_path: str = "data/tech_debt_report.json"):
        report = self.generate_report()
        out = self.repo_path / output_path
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        return str(out), report

if __name__ == "__main__":
    reporter = TechDebtReporter(repo_path=".")
    path, rep = reporter.save_json()
    print(f"Report saved to {path}")
    print(f"Summary: {rep['summary']}")
