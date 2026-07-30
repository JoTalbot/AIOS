#!/usr/bin/env python3
"""Dead Code Hunter"""
import json
import subprocess
import os
import re

def find_python_files(root="/mnt/agents/-Octopus/repo"):
    result = subprocess.run(["find", root, "-name", "*.py", "-not", "-path", "*/\.*", "-not", "-path", "*/venv/*"], 
                          capture_output=True, text=True, timeout=60)
    return [f for f in result.stdout.split("\n") if f and "__pycache__" not in f][:50]

def check_unused_imports(filepath):
    """Simple check for unused imports"""
    try:
        with open(filepath) as f:
            content = f.read()
        
        imports = re.findall(r"^(?:from|import)\s+(\w+)", content, re.MULTILINE)
        issues = []
        for imp in imports:
            if imp in content.split(imp)[1].split("import")[0] if "import" in content else True:
                if content.count(imp) < 3:  # Minimal usage check
                    issues.append(imp)
        return issues[:5]
    except:
        return []

def check_main_results():
    """Check for main() not called"""
    files_without_main_check = []
    for f in find_python_files()[:20]:
        try:
            with open(f) as fp:
                content = fp.read()
            if "def main()" in content and "if __name__" not in content:
                files_without_main_check.append(f)
        except:
            pass
    return files_without_main_check

if __name__ == "__main__":
    files = find_python_files()
    no_main = check_main_results()
    
    print(json.dumps({
        "ok": True,
        "files_scanned": len(files),
        "files_without_main_check": len(no_main),
        "no_main_examples": no_main[:5],
        "recommendation": f"Review {len(no_main)} files without __name__ guard" if no_main else "Code structure OK"
    }, indent=2))
