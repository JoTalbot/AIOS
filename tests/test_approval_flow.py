"""Tests for approval manager."""

from aios_core.approval_manager import ApprovalManager


def test_approval_manager_init():
    am = ApprovalManager()
    assert am is not None
