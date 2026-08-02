"""RepoMap-lite (п.7 плана внедрения, аналог Aider RepoMap в миниатюре).

AST-карта модулей aios_core -> топ-уровневые символы (классы/функции/константы).
Кэшируется в data/.repomap.json, инвалидируется по (mtime, size) сигнатуре —
пересборка только при изменении файлов.

Используется планировщиком (run_coder_orchestrator.phase_plan), чтобы LLM
выбирал файл задачи, зная его содержимое, а не вслепую по имени.
"""
from __future__ import annotations

import ast
import json
import os
from pathlib import Path

REPO = Path(os.environ.get("AIOS_REPO_PATH", "/root/AIOS"))
CACHE = REPO / "data" / ".repomap.json"
SCOPE = "aios_core"
MAX_SYMS_PER_FILE = 8


def _symbols(path: Path) -> list[str]:
    """Топ-уровневые символы файла (до MAX_SYMS_PER_FILE)."""
    try:
        tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
    except Exception:
        return []
    syms: list[str] = []
    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            syms.append(f"class {node.name}")
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            syms.append(f"{node.name}()")
        elif (isinstance(node, ast.Assign) and len(node.targets) == 1
              and isinstance(node.targets[0], ast.Name) and node.targets[0].id.isupper()):
            syms.append(node.targets[0].id)
    return syms[:MAX_SYMS_PER_FILE]


def _scope_files() -> list[Path]:
    base = REPO / SCOPE
    if not base.is_dir():
        return []
    return sorted(p for p in base.rglob("*.py") if "__pycache__" not in p.parts)


def _signature(files: list[Path]) -> dict[str, list[int]]:
    sig: dict[str, list[int]] = {}
    for p in files:
        try:
            st = p.stat()
        except OSError:
            continue
        sig[str(p.relative_to(REPO))] = [int(st.st_mtime), st.st_size]
    return sig


def build(force: bool = False) -> dict[str, list[str]]:
    """{относительный/путь.py: [символы]}; кэш с инвалидацией по сигнатуре."""
    files = _scope_files()
    sig = _signature(files)
    if not force and CACHE.is_file():
        try:
            cached = json.loads(CACHE.read_text(encoding="utf-8"))
            if cached.get("sig") == sig:
                return cached.get("map", {})
        except Exception:
            pass
    repo_map: dict[str, list[str]] = {}
    for p in files:
        rel = str(p.relative_to(REPO))
        syms = _symbols(p)
        if syms:
            repo_map[rel] = syms
    try:
        CACHE.write_text(json.dumps({"sig": sig, "map": repo_map},
                                    ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass
    return repo_map


def map_summary(max_chars: int = 1400) -> str:
    """Компактная многострочная сводка для LLM-промпта (~max_chars)."""
    repo_map = build()
    lines: list[str] = []
    used = 0
    for rel in sorted(repo_map):
        line = f"{rel}: {', '.join(repo_map[rel])}"
        if used + len(line) > max_chars:
            if lines:
                lines.append(f"… (+{len(repo_map) - len(lines)} модулей)")
            break
        lines.append(line)
        used += len(line) + 1
    return "\n".join(lines)


if __name__ == "__main__":
    import sys
    print(map_summary(int(sys.argv[1]) if len(sys.argv) > 1 else 1400))
