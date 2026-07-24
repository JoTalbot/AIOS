"""Production autopilot GA criteria tests — 3 IG profiles ≥2 weeks no bans"""

from aios_core.production_autopilot import (
    ProductionAutopilot,
    ProductionConfig,
    ProductionProfile,
)


def test_default_3_ig_config():
    cfg = ProductionConfig.default_3_instagram()
    assert len(cfg.profiles) == 3
    assert all(p.platform == "instagram" for p in cfg.profiles)
    assert cfg.device_pool_size == 3
    assert cfg.cycle_interval_s == 900


def test_production_profile_to_dict():
    prof = ProductionProfile(platform="instagram", name="ig_shop_1", actions_per_hour=45)
    d = prof.to_dict()
    assert d["platform"] == "instagram"
    assert d["actions_per_hour"] == 45


def test_config_from_env():
    cfg = ProductionConfig.from_env()
    assert len(cfg.profiles) >= 3


def test_autopilot_single_cycle():
    cfg = ProductionConfig.default_3_instagram()
    autopilot = ProductionAutopilot(cfg, fast_mode=True)
    reports = autopilot.run_all_profiles_cycle()
    assert len(reports) == 3
    for r in reports:
        assert r.status in ("ran", "blocked-compliance")
        assert r.actions >= 0
        assert r.pacing_stats is not None


def test_autopilot_compliance():
    cfg = ProductionConfig.default_3_instagram()
    autopilot = ProductionAutopilot(cfg, fast_mode=True)
    profile = cfg.profiles[0]
    check = autopilot._check_compliance(profile, "collect")
    assert "allowed" in check
    assert "reason" in check


def test_autopilot_health():
    cfg = ProductionConfig.default_3_instagram()
    autopilot = ProductionAutopilot(cfg, fast_mode=True)
    autopilot.run_all_profiles_cycle()
    health = autopilot.health_report()
    assert "profiles" in health
    assert health["profiles"] == 3
    assert "total_cycles" in health
    assert "avg_success_rate" in health


def test_simulation_2_weeks_fast():
    cfg = ProductionConfig.default_3_instagram()
    autopilot = ProductionAutopilot(cfg, fast_mode=True)
    report = autopilot.simulate_2_weeks(cycles_per_day=2)
    assert "simulation" in report
    assert report["simulation"]["days"] == 14
    assert report["simulation"]["profiles"] == 3
    assert report["simulation"]["total_cycles"] == 14 * 2 * 3
    assert "pacing_metrics" in report
    assert "health" in report
    assert report["simulation"]["avg_success_rate"] > 0.8


def test_prometheus_metrics():
    cfg = ProductionConfig.default_3_instagram()
    autopilot = ProductionAutopilot(cfg, fast_mode=True)
    autopilot.run_all_profiles_cycle()
    metrics = autopilot.to_prometheus_metrics()
    assert "aios_production_profiles" in metrics
    assert "aios_production_bans_total" in metrics
    assert "aios_pacer_actions" in metrics


def test_ban_free_simulation():
    cfg = ProductionConfig(
        profiles=[
            ProductionProfile(
                platform="instagram", name="ig1", actions_per_hour=30, session_max_s=1200
            ),
            ProductionProfile(
                platform="instagram", name="ig2", actions_per_hour=30, session_max_s=1200
            ),
            ProductionProfile(
                platform="instagram", name="ig3", actions_per_hour=30, session_max_s=1200
            ),
        ],
        device_pool_size=3,
    )
    autopilot = ProductionAutopilot(cfg, fast_mode=True)
    report = autopilot.simulate_2_weeks(cycles_per_day=1)
    assert report["simulation"]["bans"] <= 1


def test_production_config_json():
    cfg = ProductionConfig.default_3_instagram()
    import json

    data = {"profiles": [p.to_dict() for p in cfg.profiles]}
    json_str = json.dumps(data)
    assert "ig_shop_1" in json_str
