"""Verify tools/ and scripts/ directories."""

from pathlib import Path


def test_tools_directory_exists():
    root = Path(__file__).parent.parent
    assert (root / "tools").exists()


def test_scripts_directory_exists():
    root = Path(__file__).parent.parent
    assert (root / "scripts").exists()


def test_deploy_directory_exists():
    root = Path(__file__).parent.parent
    assert (root / "deploy").exists()


def test_monitor_script_exists():
    root = Path(__file__).parent.parent
    assert (root / "monitor.py").exists()


def test_run_rest_api_exists():
    root = Path(__file__).parent.parent
    assert (root / "run_rest_api.py").exists()
