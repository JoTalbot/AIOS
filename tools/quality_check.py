#!/usr/bin/env python3
"""AIOS quality gate checker — validates all code-quality invariants."""

import ast
import os
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent


def check_bare_excepts() -> int:
    """Count bare except: clauses (should be 0)."""
    count = 0
    for py_file in (ROOT / "aios_core").rglob("*.py"):
        if py_file.name.startswith("__"): continue
        for i, line in enumerate(open(py_file), 1):
            if line.strip() == "except:" and "noqa" not in line:
                print(f"❌ {py_file.relative_to(ROOT)}:{i}: bare except")
                count += 1
    return count


def check_unannotated_passes() -> int:
    """Count pass blocks without explanatory comment."""
    count = 0
    for py_file in (ROOT / "aios_core").rglob("*.py"):
        if py_file.name.startswith("__"): continue
        lines = open(py_file).readlines()
        for i, line in enumerate(lines):
            if line.strip().startswith("except") and i + 1 < len(lines):
                if lines[i + 1].strip() == "pass":
                    count += 1
                    print(f"⚠️  {py_file.relative_to(ROOT)}:{i+1}: pass without comment")
    return count


def check_compile() -> int:
    """Count files that fail AST parse."""
    errors = 0
    for py_file in (ROOT / "aios_core").rglob("*.py"):
        try: ast.parse(py_file.read_text())
        except SyntaxError as e:
            print(f"❌ {py_file.relative_to(ROOT)}: {e}")
            errors += 1
    return errors


def check_docstrings() -> tuple:
    """Return (total_public, undocumented)."""
    total = undoc = 0
    for py_file in (ROOT / "aios_core").rglob("*.py"):
        if py_file.name.startswith("__"): continue
        try: tree = ast.parse(py_file.read_text())
        except: continue
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and not node.name.startswith("_"):
                total += 1
                has_doc = (node.body and isinstance(node.body[0], ast.Expr) and
                          isinstance(node.body[0].value, ast.Constant))
                if not has_doc: undoc += 1
    return total, undoc


def main():
    print("🔍 AIOS Quality Gate Checker\n")
    
    bare = check_bare_excepts()
    print(f"  Bare excepts: {bare}", "✅" if bare == 0 else "❌")
    
    passes = check_unannotated_passes()
    print(f"  Unannotated passes: {passes}", "✅" if passes == 0 else "⚠️")
    
    compile_errors = check_compile()
    print(f"  Compile errors: {compile_errors}", "✅" if compile_errors == 0 else "❌")
    
    total, undoc = check_docstrings()
    pct = 100 * (total - undoc) / max(total, 1)
    print(f"  Docstrings: {total - undoc}/{total} ({pct:.1f}%)")
    
    test_files = sum(1 for _ in (ROOT / "tests").rglob("test_*.py"))
    test_funcs = 0
    for f in (ROOT / "tests").rglob("test_*.py"):
        test_funcs += len([l for l in open(f) if l.strip().startswith("def test_")])
    print(f"  Test files: {test_files}")
    print(f"  Test functions: {test_funcs}")
    
    all_ok = bare == 0 and passes == 0 and compile_errors == 0
    print(f"\n{'✅ ALL GATES PASS' if all_ok else '❌ ISSUES FOUND'}")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
