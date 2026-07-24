"""Tests for aios_core/android_driver.py"""
from __future__ import annotations
import pytest
from aios_core.android_driver import DriverPool


class TestDriverPool:
    def test_create(self):
        pool = DriverPool()
        assert pool is not None

    def test_stats(self):
        pool = DriverPool()
        s = pool.stats()
        assert isinstance(s, dict)
