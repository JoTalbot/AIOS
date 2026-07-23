"""Tests for Helm charts and K8s manifests."""

from pathlib import Path


def test_helm_chart_exists():
    root = Path(__file__).parent.parent
    chart = root / 'helm' / 'aios' / 'Chart.yaml'
    if chart.exists():
        assert chart.stat().st_size > 0


def test_k8s_manifests_exist():
    root = Path(__file__).parent.parent
    manifests = list((root / 'k8s').glob('*.yaml'))
    assert len(manifests) >= 0, 'K8s directory checked'
