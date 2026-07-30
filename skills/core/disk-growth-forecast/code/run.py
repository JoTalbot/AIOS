#!/usr/bin/env python3
"""Disk Growth Forecast"""
import json
import sys
import subprocess
from datetime import datetime, timedelta

def get_disk_history():
    """Get disk usage history from df logs"""
    # Simplified: just current usage
    result = subprocess.run(["df", "-h", "/"], capture_output=True, text=True)
    lines = result.stdout.strip().split("\n")
    if len(lines) > 1:
        parts = lines[1].split()
        return {
            "total_gb": float(parts[1].rstrip("G")),
            "used_gb": float(parts[2].rstrip("G")),
            "available_gb": float(parts[3].rstrip("G")),
            "percent": int(parts[4].rstrip("%"))
        }
    return {}

def estimate_daily_growth(history_days=7):
    """Estimate daily growth rate (simplified)"""
    # Default 0.5 GB/day if no history
    return 0.5

def forecast_disk(days_ahead=30):
    disk = get_disk_history()
    if not disk:
        return {"error": "Cannot read disk"}
    
    current_percent = disk.get("percent", 0)
    available_gb = disk.get("available_gb", 0)
    
    # Estimate days until full
    daily_growth = estimate_daily_growth()
    if daily_growth > 0:
        days_until_full = available_gb / daily_growth
    else:
        days_until_full = 999
    
    # Determine status
    if days_until_full > 30:
        status = "OK"
    elif days_until_full > 14:
        status = "WARNING"
    elif days_until_full > 7:
        status = "ALERT"
    else:
        status = "CRITICAL"
    
    full_date = datetime.now() + timedelta(days=days_until_full)
    
    return {
        "current_percent": current_percent,
        "available_gb": round(available_gb, 2),
        "daily_growth_gb": daily_growth,
        "days_until_full": round(days_until_full, 1),
        "estimated_full_date": full_date.strftime("%Y-%m-%d"),
        "status": status,
        "recommendation": get_recommendation(status, days_until_full)
    }

def get_recommendation(status, days):
    if status == "CRITICAL":
        return "Срочно чистить! Менее 7 дней до заполнения."
    elif status == "ALERT":
        return "Планировать cleanup в ближайшую неделю."
    elif status == "WARNING":
        return "Мониторить, планировать cleanup."
    else:
        return "Всё хорошо. Запас >30 дней."

if __name__ == "__main__":
    result = forecast_disk()
    print(json.dumps({"ok": True, "forecast": result}, indent=2))
