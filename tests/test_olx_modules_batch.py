"""Tests for OLX storage and scheduler modules."""

import os
import sys

# Ensure modules/olx is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_olx_storage_imports():
    """Verify OLX storage module can be imported."""
    from aios_core.modules.olx.storage import OLXStorage

    assert OLXStorage is not None


def test_olx_collector_imports():
    """Verify OLX collector module can be imported."""
    from aios_core.modules.olx.collector import OLXCollector

    assert OLXCollector is not None


def test_olx_competitor_imports():
    """Verify OLX competitor analyzer imports."""
    from aios_core.modules.olx.competitive import CompetitorAnalyzer

    assert CompetitorAnalyzer is not None


def test_olx_scheduler_imports():
    """Verify OLX scheduler imports."""
    from aios_core.modules.olx.scheduler import CollectionScheduler

    assert CollectionScheduler is not None
