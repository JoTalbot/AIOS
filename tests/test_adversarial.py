"""Tests for Adversarial Robustness."""

from aios_core.adversarial import AdversarialDefense


def test_detect_no_anomaly():
    ad = AdversarialDefense()
    result = ad.detect_adversarial([0.1, 0.15, 0.12])
    assert result is False
    assert ad.stats()["attacks_detected"] == 0


def test_detect_anomaly():
    ad = AdversarialDefense()
    result = ad.detect_adversarial([0.0, 1.0, 0.5])
    assert result is True
    assert ad.stats()["attacks_detected"] == 1


def test_detect_empty_list():
    ad = AdversarialDefense()
    result = ad.detect_adversarial([])
    assert result is False


def test_adversarial_training_returns_status():
    ad = AdversarialDefense()
    result = ad.adversarial_training(None, [1, 2, 3], [4, 5])
    assert result["status"] == "completed"
    assert result["samples"] == 5


def test_stats_initial():
    ad = AdversarialDefense()
    assert ad.stats() == {"attacks_detected": 0}
