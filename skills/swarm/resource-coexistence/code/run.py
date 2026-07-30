#!/usr/bin/env python3
"""resource-coexistence — bounded read-only auditor for host resource coexistence.

Implements instruction #18 section 4: heavy services (ollama, ipfs, docker, ...)
MUST have CPU/RAM limits so the human always retains resources on a shared host.
Also checks host headroom (RAM/CPU/disk) for human coexistence.

SAFETY CONTRACT
- Read-only: never sets/changes any cgroup limit, never stops a service.
- Emits a coexistence dashboard + drift findings + host-headroom report.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

SKILL_DIR = Path(__file__).resolve().parents[1]

# Heavy services that per #18/#22 SHOULD have cgroup limits when active.
# (unit, expected_cpu_quota_pct_max, expected_mem_bytes_min)
# These are services documented in #22 as resource-heavy.
HEAVY_SERVICES = [
    ("ollama.service", 300, 2 * 1024 ** 3),                     # #22: CPUQuota=200%, MemoryMax=4G
    ("octopus-ubu-whisper-worker.service", 400, 2 * 1024 ** 3), # #22: 6G whisper
    ("ipfs.service", 400, 1 * 1024 ** 3),                       # IPFS node
    ("docker.service", 600, None),                              # docker daemon; CPU+mem, mem required when children run
]

# Host headroom thresholds — the human should always have at least this free.
MIN_FREE_RAM_FRACTION = 0.20   # >=20% RAM available to the human
MIN_FREE_DISK_FRACTION = 0.10  # >=10% disk free (matches #42: parent needs >=1GB)
DISK_CRITICAL_FRACTION = 0.05   # <5% disk free = critical


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------- cgroup limit parsing (pure) ----------

def parse_cpu_quota(raw: str) -> Optional[int]:
    """Parse a systemd CPUQuotaPerSecUSec value into a percentage (of one core).

    systemd reports e.g. '2s' (= 200%), 'infinity' (= unlimited), '1s500ms' (=150%).
    Returns None for unlimited/invalid.
    """
    if not raw or raw.strip() in ("infinity", "0", ""):
        return None
    # format: e.g. "2s", "1s500ms", "200ms"
    total_us = 0
    m = re.match(r"(?:(\d+)s)?(?:(\d+)ms)?", raw.strip())
    if not m:
        return None
    secs = int(m.group(1) or 0)
    ms = int(m.group(2) or 0)
    total_us = secs * 1_000_000 + ms * 1000
    if total_us <= 0:
        return None
    return round(total_us / 10_000)  # 1_000_000 us = 100%


def parse_mem_bytes(raw: str) -> Optional[int]:
    """Parse a systemd MemoryMax/MemoryHigh value into bytes.
    'infinity' or absent -> None (unlimited)."""
    if not raw or raw.strip() in ("infinity", "0", ""):
        return None
    try:
        return int(raw.strip())
    except ValueError:
        return None


def has_cpu_limit(pct: Optional[int]) -> bool:
    return pct is not None and pct > 0


def has_mem_limit(b: Optional[int]) -> bool:
    return b is not None and b > 0


# ---------- classification (pure, testable) ----------

def classify_service(
    name: str,
    active: str,
    cpu_pct: Optional[int],
    mem_bytes: Optional[int],
    cpu_cap: int,
    mem_floor: Optional[int],
) -> Dict[str, Any]:
    """Classify one heavy service by its limit state."""
    is_on = active in ("active", "yes", "running")
    cpu_ok = has_cpu_limit(cpu_pct)
    mem_ok = has_mem_limit(mem_bytes)
    result: Dict[str, Any] = {
        "unit": name,
        "active": active,
        "cpu_quota_pct": cpu_pct,
        "memory_max_bytes": mem_bytes,
        "has_cpu_limit": cpu_ok,
        "has_mem_limit": mem_ok,
        "state": "",
    }
    if not is_on:
        result["state"] = "inactive"
        return result
    if mem_floor is not None:
        if not mem_ok:
            result["state"] = "active_unlimited_mem"
            return result
        if mem_bytes < mem_floor:
            result["state"] = "active_low_mem_limit"
            return result
    if not cpu_ok:
        result["state"] = "active_unlimited_cpu"
        return result
    if cpu_cap and cpu_pct > cpu_cap:
        result["state"] = "active_high_cpu_limit"
        return result
    result["state"] = "active_limited_ok"
    return result


# ---------- drift detection (pure) ----------

def detect_drift(services: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    findings: List[Dict[str, Any]] = []
    for s in services:
        st = s["state"]
        unit = s["unit"]
        if st == "active_unlimited_mem":
            findings.append({
                "type": "active_no_memory_limit",
                "severity": "high",
                "unit": unit,
                "detail": f"{unit} is active with no MemoryMax — can OOM the host, violating coexistence (#18 section 4)",
            })
        elif st == "active_unlimited_cpu":
            findings.append({
                "type": "active_no_cpu_limit",
                "severity": "medium",
                "unit": unit,
                "detail": f"{unit} is active with no CPUQuota — can starve the human's processes (#18 section 4)",
            })
        elif st == "active_high_cpu_limit":
            findings.append({
                "type": "active_high_cpu_limit",
                "severity": "low",
                "unit": unit,
                "detail": f"{unit} CPUQuota={s['cpu_quota_pct']}% exceeds expected cap; review whether the human retains headroom",
            })
        elif st == "active_low_mem_limit":
            findings.append({
                "type": "active_low_memory_limit",
                "severity": "low",
                "unit": unit,
                "detail": f"{unit} MemoryMax below expected floor; service may be over-constrained",
            })
    return findings


# ---------- host headroom ----------

def host_headroom(meminfo_text: Optional[str] = None, df_text: Optional[str] = None) -> Dict[str, Any]:
    """Compute human-facing host headroom from /proc/meminfo and `df`.
    Pure-ish: takes optional text for testability."""
    headroom: Dict[str, Any] = {}
    # RAM
    if meminfo_text:
        total = _grep_int(meminfo_text, r"MemTotal:")
        avail = _grep_int(meminfo_text, r"MemAvailable:")
        if total and avail:
            free_frac = avail / total
            headroom["ram"] = {
                "total_bytes": total, "available_bytes": avail,
                "available_fraction": round(free_frac, 3),
                "ok": free_frac >= MIN_FREE_RAM_FRACTION,
            }
    # Disk
    if df_text:
        line = [l for l in df_text.splitlines() if l.strip() and "/" in l][-1:]
        if line:
            parts = line[0].split()
            if len(parts) >= 6:
                try:
                    used_pct = int(parts[4].rstrip("%"))
                    free_frac = (100 - used_pct) / 100
                    headroom["disk"] = {
                        "used_percent": used_pct,
                        "free_fraction": round(free_frac, 3),
                        "ok": free_frac >= MIN_FREE_DISK_FRACTION,
                        "critical": free_frac < DISK_CRITICAL_FRACTION,
                    }
                except ValueError:
                    pass
    return headroom


def _grep_int(text: str, key: str) -> Optional[int]:
    m = re.search(key + r"\s+(\d+)", text)
    return int(m.group(1)) * 1024 if m else None  # /proc/meminfo is in kB


# ---------- systemd integration ----------

def _show(unit: str, prop: str) -> str:
    try:
        return subprocess.run(
            ["systemctl", "show", unit, "-p", prop, "--value"],
            capture_output=True, text=True, timeout=6,
        ).stdout.strip()
    except Exception:
        return ""


def _is_active(unit: str) -> str:
    try:
        return subprocess.run(
            ["systemctl", "is-active", unit],
            capture_output=True, text=True, timeout=6,
        ).stdout.strip()
    except Exception:
        return "unknown"


def inspect_services(live: bool = True) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for unit, cpu_cap, mem_floor in HEAVY_SERVICES:
        if live:
            active = _is_active(unit)
            cpu_pct = parse_cpu_quota(_show(unit, "CPUQuotaPerSecUSec"))
            mem_bytes = parse_mem_bytes(_show(unit, "MemoryMax"))
        else:
            active, cpu_pct, mem_bytes = "unknown", None, None
        out.append(classify_service(unit, active, cpu_pct, mem_bytes, cpu_cap, mem_floor))
    return out


def _read_proc_meminfo() -> str:
    try:
        return Path("/proc/meminfo").read_text()
    except OSError:
        return ""


def _read_df_root() -> str:
    try:
        return subprocess.run(["df", "-P", "/"], capture_output=True, text=True, timeout=6).stdout
    except Exception:
        return ""


# ---------- full report ----------

def run(live: bool = True) -> Dict[str, Any]:
    services = inspect_services(live=live)
    drifts = detect_drift(services)
    headroom: Dict[str, Any] = {}
    if live:
        headroom = host_headroom(_read_proc_meminfo(), _read_df_root())
    headroom_drifts: List[Dict[str, Any]] = []
    if headroom.get("ram") and not headroom["ram"]["ok"]:
        headroom_drifts.append({
            "type": "low_ram_headroom", "severity": "high",
            "detail": f"Only {headroom['ram']['available_fraction']*100:.0f}% RAM available; human coexistence at risk (#18)",
        })
    if headroom.get("disk"):
        if headroom["disk"].get("critical"):
            headroom_drifts.append({
                "type": "disk_critical", "severity": "critical",
                "detail": f"Disk free only {headroom['disk']['free_fraction']*100:.0f}%; below 5% critical threshold",
            })
        elif not headroom["disk"]["ok"]:
            headroom_drifts.append({
                "type": "low_disk_headroom", "severity": "medium",
                "detail": f"Disk free only {headroom['disk']['free_fraction']*100:.0f}%; cleanup advised (#42)",
            })
    all_drifts = drifts + headroom_drifts
    ok = not any(f["severity"] == "critical" for f in all_drifts)
    recommendations = []
    for d in drifts:
        if d["type"] == "active_no_memory_limit":
            recommendations.append(f"Set MemoryMax on {d['unit']} (e.g. `systemctl set-property {d['unit']} MemoryMax=...`) — see #22.")
        if d["type"] == "active_no_cpu_limit":
            recommendations.append(f"Set CPUQuota on {d['unit']} — see #22.")
    if headroom.get("disk") and not headroom["disk"]["ok"]:
        recommendations.append("Run `octopus clean` or review /var/log archives — disk headroom low (#42).")
    if not all_drifts:
        recommendations.append("Coexistence state nominal: heavy services limited, host retains headroom for the human.")
    return {
        "ok": ok,
        "skill": "resource-coexistence",
        "timestamp": _now(),
        "read_only": True,
        "instruction_ref": "#18 (section 4), #22, #42",
        "host_headroom": headroom,
        "services": services,
        "drifts": all_drifts,
        "recommendations": recommendations,
    }


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser(description="Bounded read-only resource-coexistence auditor (#18 sec.4)")
    ap.add_argument("--no-live", action="store_true")
    ap.add_argument("--json", action="store_true", default=True)
    args = ap.parse_args()
    report = run(live=not args.no_live)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
