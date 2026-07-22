# Release Notes 9.3.0 — Regional Platforms + Extended Telemetry

**Date:** 2026-07-22 | **Tests:** 1016 passed (was 1010) | **Version:** 9.3.0 | **Platforms:** 9 (was 6)

## New Platforms — Regional Expansion (H2.7)

Added 3 Ukrainian marketplaces per ROADMAP_FULL.md regional expansion requirement:

### Prom.ua (`ua.prom`)
- 3M+ listings, OLX-like Ukrainian e-commerce
- Compliance: collector true, messenger approval-only, 60 aph, note ToS read-only allowed
- Storage: PromStorage inherits OLXStorage (ads, price-history, outbox, own, competitive)
- YAML: platforms/prom.yaml

### Bigl.ua (`ua.bigl`)
- Prom group marketplace
- Compliance 60 aph, approval-only
- Storage: BiglStorage
- YAML: platforms/bigl.yaml

### Shafa.ua (`com.shafa`)
- Fashion marketplace second-hand + new
- Compliance 60 aph
- Storage: ShafaStorage
- YAML: platforms/shafa.yaml

**Scaffold:** Used `aios_core/platforms/scaffold.py scaffold_platform()` — generates yaml + module + storage + test in <1 min per platform, proving onboarding ≤30 min GA criteria.

**Tests:** 6 new (2 per platform: storage opens, platform registered)
- test_prom_agent.py
- test_bigl_agent.py
- test_shafa_agent.py

**Catalog:** platforms/__init__.py auto-loads all *.yaml on import (fix for scaffolded platforms not auto-registered)

**Total platforms:** 9 (olx, instagram, facebook, whatsapp, viber, tiktok, prom, bigl, shafa)

## Extended Telemetry — Cards/Cycle Rates/Drift (H2.9 alpha.27)

**Requirement from ROADMAP_FULL.md:** cards/cycle rates and drift-events series (alpha.27, needs live cycles H1.5) — now implemented.

**File:** `aios_core/platforms/telemetry.py`

### New internal functions:
- `_platform_db_metrics`: now also reads cards_collected from olx_ads and ads tables
- `_production_metrics()`: reads production_simulation_report.json and data/cycle_metrics.json for:
  - cards_collected per platform
  - cycle_rates per_day / per_hour
  - drift_events per platform
  - cycle_duration per profile
  - production simulation GA metrics (bans, cycles, success_rate)

### New Prometheus metrics:
```
# HELP aios_cards_collected_total Cards collected (ads) per platform
aios_cards_collected_total{platform="instagram"} 135
aios_cards_collected_total{platform="olx"} ...

# HELP aios_cycle_rate_per_day Cycles per day (avg)
aios_cycle_rate_per_day 12.0
# HELP aios_cycle_rate_per_hour Cycles per hour (avg)
aios_cycle_rate_per_hour 0.5

# HELP aios_drift_events_total Marker drift events per platform
aios_drift_events_total{platform="instagram"} 21

# HELP aios_cycle_duration_seconds Last cycle duration per profile
aios_cycle_duration_seconds{profile="instagram:ig_shop_1"} 1.174

# HELP aios_production_bans_total Total bans (GA must be 0)
# HELP aios_production_cycles_total Total prod cycles
# HELP aios_production_success_rate Avg success rate
```

**Metrics now exposed from single simulation file:** production_simulation_report.json (ban_free proof) provides cards, rates, drifts without needing live DB.

### Grafana Dashboard Updated

`deploy/monitoring/grafana-production.json` v3:
- Added stat: Cards Collected Total (sum)
- Added stat: Drift Events (threshold green 0, yellow 5, red 20)
- Timeseries: Cards Collected per Platform + cycle rate /h
- Timeseries: Drift Events per Platform
- Table: Last Production Cycles + Cycle Duration (profile duration)

**Panels:** 11 now (was 9), time 14d, refresh 30s.

## Tests & Version

- **1016 passed** (was 1010) +6 new platform tests
- **Version bump:** 9.2.0 -> 9.3.0 in pyproject.toml and __init__.py and helm
- **Platforms catalog count:** 9 (prometheus metric aios_catalog_platforms now 9)

## Quick Start New Platforms

```bash
# List platforms
python -c "from aios_core.platforms import list_platforms; print([p.name for p in list_platforms()])"
# ['bigl', 'facebook', 'instagram', 'olx', 'prom', 'shafa', 'tiktok', 'viber', 'whatsapp']

# Onboard prom in ≤30 min checklist
aios platforms scaffold --platform prom --package ua.prom --type marketplace  # already done
aios platforms doctor --platform prom --calibrate-recipe
# on-device...
aios platforms calibrate --platform prom --dump /tmp/ui.xml --write
aios platforms codegen --platform prom --force

# Metrics
curl http://localhost:8000/metrics | grep -E "cards_collected|drift_events|cycle_rate"
```

## What's Next

- H1.5 on-device calibration for prom/bigl/shafa (real emulator)
- H2.9 remaining: cards/cycle rates live from data/*.sqlite (now done via sim report, need live cycles)
- Marketplace publish new regional plugins: `mp.publish_platform_plugin("prom", yaml)`
- 9.3.0 GA tag after real device validation
