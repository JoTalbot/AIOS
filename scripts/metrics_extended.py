#!/usr/bin/env python3
"""
Extended metrics generator for AIOS balancer, tech debt, security
Appends to aios_service.prom
"""
import json, os, re
from pathlib import Path

def get_coder_stats():
    backlog_path = Path("/root/AIOS/data/coder_backlog.json")
    if not backlog_path.exists():
        return {}
    try:
        data = json.loads(backlog_path.read_text())
        return {
            "cycles": data.get("cycle_count", 0),
            "completed": data.get("completed", 0),
            "failed": data.get("failed", 0),
            "tasks_pending": len([t for t in data.get("tasks", []) if t.get("status")=="pending"]),
            "tasks_total": len(data.get("tasks", [])),
            "lessons": len(data.get("lessons", []))
        }
    except Exception:
        return {}

def get_balancer_stats():
    # Parse coder log for balancer OK and errors
    log_path = Path("/root/AIOS/logs/coder_orchestrator.log")
    if not log_path.exists():
        return {}
    try:
        content = log_path.read_text()[-50000:]  # last 50k
        # Count OK per provider
        ok_pattern = re.compile(r"\[Balancer\] OK: (\w+)/([\w\-\.:/]+)")
        err_pattern = re.compile(r"\[Balancer\] (\w+)/[^:]+: HTTP (\d+)")
        ok_counts = {}
        err_counts = {}
        for m in ok_pattern.finditer(content):
            prov = m.group(1)
            ok_counts[prov] = ok_counts.get(prov, 0) + 1
        for m in err_pattern.finditer(content):
            prov = m.group(1)
            err_counts[prov] = err_counts.get(prov, 0) + 1
        return {"ok": ok_counts, "err": err_counts}
    except Exception as e:
        return {"error": str(e)}

def get_tech_debt():
    report_path = Path("/root/AIOS/data/tech_debt_report.json")
    if not report_path.exists():
        report_path = Path("/root/AIOS-autocoder/data/tech_debt_report.json")
    if not report_path.exists():
        return {}
    try:
        data = json.loads(report_path.read_text())
        summary = data.get("summary", {})
        return {
            "total_todos": summary.get("total_todos", 0),
            "by_type": summary.get("by_type", {}),
            "complex": summary.get("complex_functions", 0),
            "security": summary.get("security_issues", 0)
        }
    except Exception:
        return {}

def get_security_audit():
    # Run quick audit counts
    try:
        from aios_core.security_audit import SecurityAuditor
        aud = SecurityAuditor("/root/AIOS")
        rep = aud.generate_report()
        return {
            "xss": len(rep.get("xss", [])),
            "secrets": len(rep.get("secrets", [])),
            "dangerous": len(rep.get("dangerous_calls", []))
        }
    except Exception:
        return {}

def generate_prom():
    lines = []
    # Coder stats
    coder = get_coder_stats()
    if coder:
        lines.append("# HELP aios_coder_cycles_total Total coder cycles")
        lines.append("# TYPE aios_coder_cycles_total counter")
        lines.append(f"aios_coder_cycles_total {coder.get('cycles',0)}")
        lines.append("# HELP aios_coder_completed_total Completed tasks")
        lines.append("# TYPE aios_coder_completed_total counter")
        lines.append(f"aios_coder_completed_total {coder.get('completed',0)}")
        lines.append(f"aios_coder_failed_total {coder.get('failed',0)}")
        lines.append(f"aios_coder_tasks_pending {coder.get('tasks_pending',0)}")
        lines.append(f"aios_coder_tasks_total {coder.get('tasks_total',0)}")
    
    # Balancer
    bal = get_balancer_stats()
    if bal.get("ok"):
        lines.append("# HELP aios_balancer_requests_total Requests per provider")
        lines.append("# TYPE aios_balancer_requests_total counter")
        for prov, cnt in bal["ok"].items():
            lines.append(f'aios_balancer_requests_total{{provider="{prov}"}} {cnt}')
    if bal.get("err"):
        lines.append("# HELP aios_balancer_errors_total Errors per provider")
        lines.append("# TYPE aios_balancer_errors_total counter")
        for prov, cnt in bal["err"].items():
            lines.append(f'aios_balancer_errors_total{{provider="{prov}"}} {cnt}')
    
    # Tech debt
    td = get_tech_debt()
    if td:
        lines.append("# HELP aios_tech_debt_todos_total Total TODOs")
        lines.append("# TYPE aios_tech_debt_todos_total gauge")
        lines.append(f"aios_tech_debt_todos_total {td.get('total_todos',0)}")
        by_type = td.get("by_type", {})
        for ttype, cnt in by_type.items():
            lines.append(f'aios_tech_debt_by_type{{type="{ttype}"}} {cnt}')
        lines.append(f"aios_tech_debt_complex_functions {td.get('complex',0)}")
        lines.append(f"aios_tech_debt_security_issues {td.get('security',0)}")
    
    # Security audit
    sec = get_security_audit()
    if sec:
        lines.append(f"aios_security_xss_total {sec.get('xss',0)}")
        lines.append(f"aios_security_secrets_total {sec.get('secrets',0)}")
        lines.append(f"aios_security_dangerous_calls_total {sec.get('dangerous',0)}")
    
    # Validation blocked
    try:
        log_content = Path("/root/AIOS/logs/coder_orchestrator.log").read_text()
        blocked = log_content.count("BLOCKED")
        lines.append(f"aios_coder_validation_blocked_total {blocked}")
        # Count passed
        passed = log_content.count("Status: passed")
        lines.append(f"aios_coder_validation_passed_total {passed}")
    except Exception:
        pass

    return "\n".join(lines)

if __name__ == "__main__":
    print(generate_prom())
