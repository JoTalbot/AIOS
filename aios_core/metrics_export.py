"""Prometheus text exposition for AIOS runtime state (v11.8.0).

Renders the live singletons behind the web dashboard — the agent memory
system, the substrate convergence engine and the energy-aware scheduler —
in the Prometheus text exposition format, so any Prometheus / Grafana
stack can scrape ``GET /api/metrics`` directly.

Every series is a point-in-time gauge except explicitly cumulative
counters. Rendering is pure string building: no optional dependencies,
and a missing source (e.g. memory system not seeded yet) simply omits
its block.
"""

from __future__ import annotations

import math
from typing import Any

__all__ = ["PROMETHEUS_MEDIA_TYPE", "render_prometheus"]

#: Media type for the endpoint. Starlette appends ``; charset=utf-8``,
#: producing the canonical ``text/plain; version=0.0.4; charset=utf-8``.
PROMETHEUS_MEDIA_TYPE = "text/plain; version=0.0.4"


def _label(value: Any) -> str:
    """Escape a Prometheus label value (backslash, quote, newline)."""
    return str(value).replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


def _number(value: Any) -> str:
    """Format a sample value as a finite decimal Prometheus accepts."""
    if isinstance(value, bool):
        return "1" if value else "0"
    if isinstance(value, int):
        return str(value)
    number = float(value)
    if not math.isfinite(number):
        return "0"
    text = f"{number:.6f}".rstrip("0").rstrip(".")
    return text if text and text != "-0" else "0"


def _header(lines: list[str], name: str, help_text: str, mtype: str) -> None:
    lines.append(f"# HELP {name} {help_text}")
    lines.append(f"# TYPE {name} {mtype}")


def _sample(lines: list[str], name: str, value: Any, labels: dict[str, Any] | None = None) -> None:
    if labels:
        rendered = ",".join(f'{key}="{_label(val)}"' for key, val in labels.items())
        lines.append(f"{name}{{{rendered}}} {_number(value)}")
    else:
        lines.append(f"{name} {_number(value)}")


def _render_memory(lines: list[str], memory_system: Any) -> None:
    stats = memory_system.stats()

    _header(lines, "aios_memory_entries", "Memories per pool (archive = cold storage).", "gauge")
    _sample(lines, "aios_memory_entries", stats["short_term_count"], {"pool": "short_term"})
    _sample(lines, "aios_memory_entries", stats["long_term_count"], {"pool": "long_term"})
    _sample(lines, "aios_memory_entries", stats["episodic_count"], {"pool": "episodic"})
    _sample(lines, "aios_memory_entries", (stats.get("archive") or {}).get("archived_total", 0), {"pool": "archive"})

    platform_dist = stats.get("platform_distribution") or {}
    if platform_dist:
        _header(lines, "aios_memory_platform_entries", "Active-pool memories per platform.", "gauge")
        for platform_name, count in sorted(platform_dist.items()):
            _sample(lines, "aios_memory_platform_entries", count, {"platform": platform_name})

    _header(lines, "aios_memory_patterns", "Extracted success patterns.", "gauge")
    _sample(lines, "aios_memory_patterns", stats["pattern_count"])

    _header(lines, "aios_memory_avg_strength", "Average memory strength per pool.", "gauge")
    _sample(lines, "aios_memory_avg_strength", stats["avg_strength_short"], {"pool": "short_term"})
    _sample(lines, "aios_memory_avg_strength", stats["avg_strength_long"], {"pool": "long_term"})

    dedup = stats.get("dedup") or {}
    _header(lines, "aios_memory_dedup_removed_total", "Duplicate entries merged away (cumulative).", "counter")
    _sample(lines, "aios_memory_dedup_removed_total", dedup.get("removed_total", 0))
    last = dedup.get("last_report") or {}
    if last:
        _header(lines, "aios_memory_dedup_groups", "Duplicate groups found by the last dedup run.", "gauge")
        _sample(lines, "aios_memory_dedup_groups", last.get("groups_found", 0))

    compression = stats.get("compression") or {}
    if compression:
        _header(lines, "aios_memory_compression_entries", "Entries in the compressed memory index.", "gauge")
        _sample(lines, "aios_memory_compression_entries", compression.get("entries_compressed", 0))
        _header(lines, "aios_memory_compression_ratio", "Storage savings ratio of the compressed index.", "gauge")
        _sample(lines, "aios_memory_compression_ratio", compression.get("ratio", 0))
        _header(lines, "aios_memory_compression_bytes", "Memory index footprint in bytes.", "gauge")
        _sample(lines, "aios_memory_compression_bytes", compression.get("original_bytes", 0), {"direction": "original"})
        _sample(
            lines, "aios_memory_compression_bytes", compression.get("compressed_bytes", 0), {"direction": "compressed"}
        )


def _render_engine(lines: list[str], engine: Any) -> None:
    stats = engine.stats()

    _header(lines, "aios_substrates", "Compute substrates known to the convergence engine.", "gauge")
    _sample(lines, "aios_substrates", stats["registered_substrates"], {"state": "registered"})
    _sample(lines, "aios_substrates", stats["active_substrates"], {"state": "active"})

    _header(lines, "aios_engine_dispatches_total", "Tasks dispatched by the convergence engine.", "counter")
    _sample(lines, "aios_engine_dispatches_total", stats["total_dispatches"])
    _header(lines, "aios_engine_queued_tasks", "Tasks waiting in the engine queue.", "gauge")
    _sample(lines, "aios_engine_queued_tasks", stats["queued_tasks"])
    _header(lines, "aios_engine_energy_total", "Energy cost across all engine dispatches.", "counter")
    _sample(lines, "aios_engine_energy_total", stats["total_energy_cost"])

    per_substrate = engine.analytics().get("per_substrate") or {}
    if per_substrate:
        _header(lines, "aios_engine_substrate_dispatches_total", "Engine dispatches per substrate.", "counter")
        for name, entry in sorted(per_substrate.items()):
            _sample(lines, "aios_engine_substrate_dispatches_total", entry["dispatches"], {"substrate": name})
        _header(lines, "aios_engine_substrate_energy_total", "Energy cost per substrate.", "counter")
        for name, entry in sorted(per_substrate.items()):
            _sample(lines, "aios_engine_substrate_energy_total", entry["energy_cost"], {"substrate": name})
        _header(lines, "aios_engine_substrate_avg_latency_ms", "Average estimated latency per substrate.", "gauge")
        for name, entry in sorted(per_substrate.items()):
            _sample(lines, "aios_engine_substrate_avg_latency_ms", entry["avg_latency_ms"], {"substrate": name})


def _render_scheduler(lines: list[str], scheduler: Any) -> None:
    report = scheduler.report()

    _header(lines, "aios_scheduler_dispatches_total", "Energy-aware scheduler dispatches.", "counter")
    _sample(lines, "aios_scheduler_dispatches_total", report["dispatches"])
    _header(
        lines,
        "aios_scheduler_fallback_dispatches_total",
        "Dispatches that degraded to plain engine routing.",
        "counter",
    )
    _sample(lines, "aios_scheduler_fallback_dispatches_total", report["fallback_dispatches"])

    policy_dispatches = report.get("policy_dispatches") or {}
    if policy_dispatches:
        _header(
            lines, "aios_scheduler_policy_dispatches_total", "Dispatches per requested scheduling policy.", "counter"
        )
        for name, count in sorted(policy_dispatches.items()):
            _sample(lines, "aios_scheduler_policy_dispatches_total", count, {"policy": name})

    _header(lines, "aios_scheduler_energy_spent_total", "Energy spent by policy dispatches.", "counter")
    _sample(lines, "aios_scheduler_energy_spent_total", report["energy_spent_total"])
    _header(lines, "aios_scheduler_energy_saved_total", "Energy saved vs the engine baseline.", "counter")
    _sample(lines, "aios_scheduler_energy_saved_total", report["energy_saved_vs_baseline"])
    _header(lines, "aios_scheduler_savings_pct", "Savings vs the engine baseline, percent.", "gauge")
    _sample(lines, "aios_scheduler_savings_pct", report["savings_pct"])

    budget = report.get("energy_budget")
    if budget:
        _header(lines, "aios_scheduler_budget", "Rolling energy budget state (cost units).", "gauge")
        _sample(lines, "aios_scheduler_budget", budget["limit"], {"field": "limit"})
        _sample(lines, "aios_scheduler_budget", budget["spent"], {"field": "spent"})
        _sample(lines, "aios_scheduler_budget", budget["remaining"], {"field": "remaining"})


def render_prometheus(
    *,
    memory_system: Any = None,
    engine: Any = None,
    scheduler: Any = None,
    version: Any = "unknown",
) -> str:
    """Render the Prometheus text exposition of the given live systems.

    Args:
        memory_system: ``AgentMemorySystem`` instance (memory gauges).
        engine: ``SubstrateConvergenceEngine`` instance (substrate series).
        scheduler: ``EnergyAwareScheduler`` instance (scheduler counters).
        version: build version exported in the ``aios_info`` label.

    Returns:
        Text exposition body (``text/plain; version=0.0.4``), one sample
        per line, terminated by a trailing newline.
    """
    lines: list[str] = []

    _header(lines, "aios_info", "AIOS build information (constant 1).", "gauge")
    _sample(lines, "aios_info", 1, {"version": version})

    if memory_system is not None:
        _render_memory(lines, memory_system)
    if engine is not None:
        _render_engine(lines, engine)
    if scheduler is not None:
        _render_scheduler(lines, scheduler)

    return "\n".join(lines) + "\n"
