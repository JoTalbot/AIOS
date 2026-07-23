"""Tests for PointDrive navigation."""
from aios_core.platforms.pointdrive import PointDrive
def test_pointdrive_init():
    p = PointDrive()
    assert p is not None
