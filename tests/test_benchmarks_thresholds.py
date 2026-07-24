"""Tests for benchmarks CI thresholds — regression gate configuration."""

from __future__ import annotations

from aios_core.benchmarks_thresholds import (
    THRESHOLDS,
    ThresholdConfig,
    all_thresholds,
    check_threshold,
    get_threshold,
)


def test_thresholds_list():
    """THRESHOLDS contains expected benchmark configs."""
    assert len(THRESHOLDS) == 10
    names = [t.name for t in THRESHOLDS]
    assert "core_import" in names
    assert "storage_save_ads_100" in names
    assert "rate_limiter_is_allowed" in names
    assert "vector_search_build_index_1000" in names
    assert "cross_platform_compare_500" in names


def test_threshold_config_to_dict():
    """ThresholdConfig serializes to dict."""
    config = ThresholdConfig(name="test", max_ms=100, min_rounds=5, description="Test threshold")
    d = config.to_dict()
    assert d["name"] == "test"
    assert d["max_ms"] == 100
    assert d["min_rounds"] == 5


def test_get_threshold_existing():
    """get_threshold returns config for known name."""
    t = get_threshold("core_import")
    assert t is not None
    assert t.name == "core_import"
    assert t.max_ms == 500


def test_get_threshold_missing():
    """get_threshold returns None for unknown name."""
    t = get_threshold("nonexistent_benchmark")
    assert t is None


def test_check_threshold_pass():
    """check_threshold returns pass when actual_ms ≤ max_ms."""
    result = check_threshold("rate_limiter_is_allowed", 0.5)
    assert result["status"] == "pass"
    assert result["actual_ms"] == 0.5
    assert result["over_pct"] == 0


def test_check_threshold_fail():
    """check_threshold returns fail when actual_ms > max_ms."""
    result = check_threshold("rate_limiter_is_allowed", 5.0)
    assert result["status"] == "fail"
    assert result["over_pct"] > 0


def test_check_threshold_unknown():
    """check_threshold returns unknown for nonexistent benchmark."""
    result = check_threshold("nonexistent", 10.0)
    assert result["status"] == "unknown"
    assert result["threshold_ms"] is None


def test_check_threshold_edge():
    """check_threshold passes at exact boundary."""
    t = get_threshold("storage_save_ads_100")
    result = check_threshold("storage_save_ads_100", t.max_ms)
    assert result["status"] == "pass"


def test_all_thresholds():
    """all_thresholds returns all configs as dicts."""
    configs = all_thresholds()
    assert len(configs) == 10
    assert all(isinstance(c, dict) for c in configs)
    assert all("name" in c and "max_ms" in c for c in configs)


def test_threshold_values_reasonable():
    """All threshold values are reasonable (positive, not too large)."""
    for t in THRESHOLDS:
        assert t.max_ms > 0
        assert t.max_ms <= 10000  # No benchmark should take >10s
        assert t.min_rounds >= 1
