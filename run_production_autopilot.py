#!/usr/bin/env python3
"""
AIOS Production Autopilot Runner (v9.1.0)

Runs 3 Instagram profiles under autopilot ≥2 weeks without bans.
Implements GA criteria from ROADMAP_FULL.md H3.15:

  3+ production Instagram profiles under autopilot ≥2 weeks without bans
  (pacing metrics)

Usage:
  python run_production_autopilot.py --config default_3_ig --simulate-2weeks
  python run_production_autopilot.py --config default_3_ig --daemon --interval 900
  python run_production_autopilot.py --health
  python run_production_autopilot.py --prometheus-metrics

Secrets: all from env (AIOS_WEBHOOK_URL, etc) per constitution.
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

# Ensure project root importable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from aios_core.production_autopilot import ProductionAutopilot, ProductionConfig


def load_config(name: str) -> ProductionConfig:
    if name == "default_3_ig":
        return ProductionConfig.default_3_instagram()
    if name == "from_env":
        return ProductionConfig.from_env()
    # Try JSON file
    path = Path(name)
    if path.exists():
        data = json.loads(path.read_text())
        from aios_core.production_autopilot import ProductionProfile

        profiles = [ProductionProfile(**p) for p in data.get("profiles", [])]
        return ProductionConfig(profiles=profiles)
    raise ValueError(f"Unknown config {name}: use default_3_ig, from_env, or JSON file")


def main():
    parser = argparse.ArgumentParser(description="AIOS Production Autopilot v9.1.0")
    parser.add_argument(
        "--config", default="default_3_ig", help="Config: default_3_ig, from_env, or JSON file"
    )
    parser.add_argument(
        "--simulate-2weeks",
        action="store_true",
        help="Simulate 14 days x 24 cycles in accelerated mode",
    )
    parser.add_argument(
        "--cycles-per-day", type=int, default=24, help="Cycles per day for simulation"
    )
    parser.add_argument("--daemon", action="store_true", help="Run as daemon with interval")
    parser.add_argument(
        "--interval",
        type=int,
        default=900,
        help="Interval seconds for daemon (default 900 = 15min)",
    )
    parser.add_argument("--health", action="store_true", help="Print health report and exit")
    parser.add_argument(
        "--prometheus-metrics", action="store_true", help="Print Prometheus metrics and exit"
    )
    parser.add_argument(
        "--output",
        default="production_simulation_report.json",
        help="Output file for simulation report",
    )
    parser.add_argument("--verbose", action="store_true", help="Verbose logging")

    args = parser.parse_args()

    config = load_config(args.config)

    if args.verbose:
        print("🌐 AIOS Production Autopilot v9.1.0")
        print(f"   Config: {args.config}")
        print(f"   Profiles: {len(config.profiles)} ({', '.join(p.name for p in config.profiles)})")
        print(f"   Device pool: {config.device_pool_size}")
        print(f"   Cycle interval: {config.cycle_interval_s}s")
        print()

    autopilot = ProductionAutopilot(config)

    if args.health:
        health = autopilot.health_report()
        print(json.dumps(health, indent=2, ensure_ascii=False))
        return

    if args.prometheus_metrics:
        print(autopilot.to_prometheus_metrics())
        return

    if args.simulate_2weeks:
        print(
            f"🎬 Starting 2-week simulation: {len(config.profiles)} profiles, {args.cycles_per_day} cycles/day"
        )
        print(
            f"   Expected total cycles: 14 * {args.cycles_per_day} * {len(config.profiles)} = {14*args.cycles_per_day*len(config.profiles)}"
        )
        print()

        start = time.time()
        report = autopilot.simulate_2_weeks(cycles_per_day=args.cycles_per_day)
        elapsed = time.time() - start

        print(f"\n✅ Simulation finished in {elapsed:.2f}s (accelerated)")
        print(f"   Total cycles: {report['simulation']['total_cycles']}")
        print(f"   Total actions: {report['simulation']['total_actions']}")
        print(f"   Avg success rate: {report['simulation']['avg_success_rate']*100:.2f}%")
        print(
            f"   Bans: {report['simulation']['bans']} (ban_free={report['simulation']['ban_free']})"
        )
        print(f"   Drifts: {report['simulation']['drifts']}")
        print(f"   GA criteria met: {report['simulation']['ga_criteria_met']}")
        print()

        # Write report
        Path(args.output).write_text(
            json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        print(f"💾 Report saved to {args.output}")

        # Also print pacing metrics
        print("\n📊 Pacing metrics:")
        for key, stats in report["pacing_metrics"].items():
            print(f"   {key}: {stats['actions']} actions, {stats['session_s']}s session")

        print("\n🔮 Predictive health:")
        health = report["health"]
        print(
            f"   Devices: {health['total_devices']}, critical: {health['critical']}, high: {health['high']}"
        )
        print(f"   Avg risk: {health['avg_risk']:.3f}")

        if report["simulation"]["ga_criteria_met"]:
            print("\n🎉 GA CRITERIA MET: 3+ profiles ≥2 weeks ban-free with pacing metrics!")
        else:
            print("\n⚠️  GA criteria not fully met — check bans, success rate, profile count")
            if report["simulation"]["bans"] > 0:
                print(
                    "   → Bans detected: reduce actions_per_hour, increase jitter, check compliance"
                )
            if report["simulation"]["avg_success_rate"] < 0.9:
                print("   → Success rate <90%: recalibrate hints, check selectors")

        return

    if args.daemon:
        print(f"🔄 Daemon mode: interval {args.interval}s, profiles {len(config.profiles)}")
        print("   Press Ctrl+C to stop")
        try:
            cycle_num = 0
            while True:
                cycle_num += 1
                print(f"\n--- Cycle #{cycle_num} at {time.strftime('%Y-%m-%d %H:%M:%S')} ---")
                reports = autopilot.run_all_profiles_cycle()
                for r in reports:
                    print(
                        f"   {r.profile_key}: {r.status} {r.actions} actions, {r.success}/{r.actions} success, risk {r.predictive_risk:.2f}, drafts {r.advisor_drafts}"
                    )

                if cycle_num % 10 == 0:
                    health = autopilot.health_report()
                    print(
                        f"\n📊 Health after {cycle_num} cycles: success_rate={health['avg_success_rate']*100:.1f}%, bans={health['bans']}, total_actions={health['total_actions']}"
                    )

                print(f"   Sleeping {args.interval}s...")
                time.sleep(args.interval)
        except KeyboardInterrupt:
            print("\n🛑 Daemon stopped")
            health = autopilot.health_report()
            print(json.dumps(health, indent=2, ensure_ascii=False))
        return

    # Single cycle run
    print("🚀 Running single cycle for all profiles...")
    reports = autopilot.run_all_profiles_cycle()
    for r in reports:
        print(
            f"   {r.profile_key}: {r.status} | {r.actions} actions | {r.success} success | risk {r.predictive_risk:.2f} | {r.duration_ms:.0f}ms"
        )

    health = autopilot.health_report()
    print(
        f"\n📊 Overall health: {health['total_cycles']} cycles, {health['avg_success_rate']*100:.1f}% success, bans={health['bans']}"
    )


if __name__ == "__main__":
    main()
