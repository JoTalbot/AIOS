#!/usr/bin/env python3
"""Systemd Unit Linter - Real unit file validation"""
import json
import subprocess
import os
import re

def list_units():
    result = subprocess.run(
        ["find", "/etc/systemd/system", "-name", "*.service", "-type", "f"],
        capture_output=True, text=True, timeout=10
    )
    return [f for f in result.stdout.strip().split("\n") if f]

def lint_unit(path):
    try:
        with open(path) as f:
            content = f.read()
        
        issues, warnings = [], []
        name = os.path.basename(path)
        
        # Required sections
        for section in ["[Unit]", "[Service]", "[Install]"]:
            if section not in content:
                issues.append(f"Missing: {section}")
        
        # Required fields
        if "Description=" not in content:
            issues.append("Missing: Description")
        if "ExecStart=" not in content:
            issues.append("Missing: ExecStart")
        
        # Good practices
        if "Restart=always" not in content and "Restart=on-failure" not in content:
            warnings.append("Missing: Restart policy")
        if "User=" not in content:
            warnings.append("Missing: User= (run as non-root)")
        if "[Install]" not in content:
            warnings.append("Missing: [Install] section (no enable)")
        
        # Security
        if "Root=yes" in content:
            issues.append("Security: Running as root")
        if "umask 0000" in content:
            issues.append("Security: Insecure umask")
        
        score = max(0, 100 - len(issues) * 25 - len(warnings) * 5)
        
        return {
            "name": name,
            "score": score,
            "issues": issues,
            "warnings": warnings,
            "status": "FAIL" if issues else "WARN" if warnings else "PASS"
        }
    except Exception as e:
        return {"name": path, "error": str(e)}

def main():
    units = list_units()[:50]
    results = [lint_unit(u) for u in units]
    
    passed = sum(1 for r in results if r.get("status") == "PASS")
    failed = sum(1 for r in results if r.get("status") == "FAIL")
    
    print(json.dumps({
        "ok": failed == 0,
        "units_scanned": len(results),
        "passed": passed,
        "failed": failed,
        "average_score": round(sum(r.get("score", 0) for r in results) / len(results), 1),
        "results": results[:10]  # Top 10
    }, indent=2))

if __name__ == "__main__":
    main()
