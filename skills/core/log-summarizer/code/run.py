#!/usr/bin/env python3
"""Log Summarizer"""
import json
import subprocess
import re
from collections import Counter

def get_recent_logs(unit=None, lines=100):
    cmd = ["journalctl", "-n", str(lines), "--no-pager"]
    if unit:
        cmd.extend(["-u", unit])
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.stdout

def analyze_logs(logs):
    errors = []
    warnings = []
    
    for line in logs.split("\n"):
        if "ERROR" in line or "error" in line.lower():
            errors.append(line)
        elif "WARNING" in line or "warn" in line.lower():
            warnings.append(line)
    
    error_types = Counter()
    for e in errors:
        match = re.search(r"\[(.*?)\]", e)
        if match:
            error_types[match.group(1)] += 1
    
    return {
        "total_errors": len(errors),
        "total_warnings": len(warnings),
        "top_errors": dict(error_types.most_common(5)),
        "recommendation": get_recommendation(len(errors), len(warnings))
    }

def get_recommendation(errors, warnings):
    if errors > 10:
        return "Много ошибок! Нужно разбираться."
    elif errors > 0:
        return "Есть ошибки, рекомендуется review."
    elif warnings > 5:
        return "Много warnings, мониторить."
    else:
        return "Логи чистые."

if __name__ == "__main__":
    logs = get_recent_logs(lines=50)
    result = analyze_logs(logs)
    print(json.dumps({"ok": True, "summary": result}, indent=2))
