from pathlib import Path
import json
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.generate_quant_signal_product import watch_thresholds  # noqa: E402


def test_watch_thresholds_fallback_without_calibration(tmp_path):
    up, down = watch_thresholds(tmp_path)
    assert (up, down) == (0.60, 0.40)


def test_watch_thresholds_from_calibration_quantiles(tmp_path):
    cal = {"quantiles": {"q25": 0.44, "q50": 0.46, "q75": 0.48, "q90": 0.51, "q95": 0.52}}
    (tmp_path / "ml_prob_calibration.json").write_text(json.dumps(cal))
    up, down = watch_thresholds(tmp_path)
    assert up == 0.55  # clamp(q75=0.48 -> 0.55)
    assert down == 0.44  # clamp(q25=0.44 -> 0.44)


def test_watch_thresholds_clamped_to_bands(tmp_path):
    cal = {"quantiles": {"q25": 0.20, "q75": 0.90}}
    (tmp_path / "ml_prob_calibration.json").write_text(json.dumps(cal))
    up, down = watch_thresholds(tmp_path)
    assert up == 0.65
    assert down == 0.35
