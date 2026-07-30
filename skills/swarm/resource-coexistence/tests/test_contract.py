#!/usr/bin/env python3
"""Contract tests for resource-coexistence. Pure-logic tests, no live systemd."""
import importlib.util
from pathlib import Path

HERE = Path(__file__).resolve()
RUNTIME = HERE.parent.parent / "code" / "run.py"
assert RUNTIME.exists()
spec = importlib.util.spec_from_file_location("rco", RUNTIME)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


# ---------- cgroup parsing ----------

def test_parse_cpu_quota_seconds():
    assert mod.parse_cpu_quota("2s") == 200      # 2 cores
    assert mod.parse_cpu_quota("3s") == 300

def test_parse_cpu_quota_ms():
    assert mod.parse_cpu_quota("1s500ms") == 150
    assert mod.parse_cpu_quota("500ms") == 50

def test_parse_cpu_quota_infinity():
    assert mod.parse_cpu_quota("infinity") is None
    assert mod.parse_cpu_quota("") is None

def test_parse_mem_bytes():
    assert mod.parse_mem_bytes("4294967296") == 4294967296
    assert mod.parse_mem_bytes("infinity") is None
    assert mod.parse_mem_bytes("") is None


# ---------- classification ----------

def test_classify_active_limited_ok():
    s = mod.classify_service("ollama.service", "active", 200, 4 * 1024**3, 300, 2 * 1024**3)
    assert s["state"] == "active_limited_ok"
    assert s["has_cpu_limit"] is True
    assert s["has_mem_limit"] is True

def test_classify_inactive():
    s = mod.classify_service("ipfs.service", "inactive", None, None, 400, 1 * 1024**3)
    assert s["state"] == "inactive"

def test_classify_active_unlimited_mem():
    s = mod.classify_service("docker.service", "active", 200, None, 600, 1 * 1024**3)
    assert s["state"] == "active_unlimited_mem"

def test_classify_active_unlimited_cpu():
    # mem floor None means mem not required; cpu unlimited
    s = mod.classify_service("docker.service", "active", None, None, 600, None)
    assert s["state"] == "active_unlimited_cpu"

def test_classify_active_high_cpu():
    s = mod.classify_service("x.service", "active", 500, 4 * 1024**3, 300, 2 * 1024**3)
    assert s["state"] == "active_high_cpu_limit"

def test_classify_active_low_mem():
    s = mod.classify_service("x.service", "active", 200, 512 * 1024**2, 300, 2 * 1024**3)
    assert s["state"] == "active_low_mem_limit"


# ---------- drift detection ----------

def test_drift_unlimited_mem_is_high():
    services = [mod.classify_service("docker.service", "active", 200, None, 600, 1*1024**3)]
    d = mod.detect_drift(services)
    assert any(x["type"] == "active_no_memory_limit" and x["severity"] == "high" for x in d)

def test_drift_unlimited_cpu_is_medium():
    services = [mod.classify_service("docker.service", "active", None, None, 600, None)]
    d = mod.detect_drift(services)
    assert any(x["type"] == "active_no_cpu_limit" and x["severity"] == "medium" for x in d)

def test_drift_limited_ok_clean():
    services = [mod.classify_service("ollama.service", "active", 200, 4*1024**3, 300, 2*1024**3)]
    assert mod.detect_drift(services) == []

def test_drift_inactive_clean():
    services = [mod.classify_service("ipfs.service", "inactive", None, None, 400, 1*1024**3)]
    assert mod.detect_drift(services) == []


# ---------- host headroom ----------

def test_host_headroom_ram_ok():
    mi = "MemTotal:      12000000 kB\nMemAvailable:  8000000 kB\n"
    h = mod.host_headroom(meminfo_text=mi)
    assert h["ram"]["ok"] is True
    assert h["ram"]["available_fraction"] > 0.2

def test_host_headroom_ram_low():
    mi = "MemTotal:      12000000 kB\nMemAvailable:  1000000 kB\n"
    h = mod.host_headroom(meminfo_text=mi)
    assert h["ram"]["ok"] is False

def test_host_headroom_disk_ok():
    df = "Filesystem  1K-blocks  Used  Avail  Use%  Mounted\n/dev/sda2   109G  79G  25G  76%  /\n"
    h = mod.host_headroom(df_text=df)
    assert h["disk"]["ok"] is True
    assert h["disk"]["critical"] is False

def test_host_headroom_disk_critical():
    df = "Filesystem  1K-blocks  Used  Avail  Use%  Mounted\n/dev/sda2   109G  105G  3G  97%  /\n"
    h = mod.host_headroom(df_text=df)
    assert h["disk"]["critical"] is True


# ---------- full run ----------

def test_run_no_live_clean():
    r = mod.run(live=False)
    assert r["ok"] is True
    assert r["read_only"] is True
    assert r["drifts"] == []
