#!/usr/bin/env python3
"""Incident Triage Classifier"""
import json
import sys

def classify_incident(metrics):
    disk = metrics.get("disk_percent", 0)
    error_rate = metrics.get("error_rate", 0)
    
    if disk > 95 or error_rate > 50:
        severity = "SEV1_CRITICAL"
    elif disk > 85 or error_rate > 20:
        severity = "SEV2_HIGH"
    elif disk > 75 or error_rate > 10:
        severity = "SEV3_MEDIUM"
    else:
        severity = "SEV4_LOW"
    
    incident_type = "disk_full" if disk > 80 else "high_error_rate" if error_rate > 5 else "unknown"
    
    recommendations = {
        "SEV1_CRITICAL": "Немедленное действие!",
        "SEV2_HIGH": "Приоритетное исправление.",
        "SEV3_MEDIUM": "Планировать исправление.",
        "SEV4_LOW": "Можно отложить."
    }
    
    return {
        "severity": severity,
        "type": incident_type,
        "recommendation": recommendations[severity]
    }

if __name__ == "__main__":
    metrics = {"disk_percent": 80, "error_rate": 5}
    if len(sys.argv) > 1:
        metrics = json.loads(sys.argv[1])
    result = classify_incident(metrics)
    print(json.dumps({"ok": True, "incident": result, "metrics": metrics}, indent=2))
