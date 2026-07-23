"""Verify SDK file integrity."""

from pathlib import Path


def test_sdk_file_exists():
    root = Path(__file__).parent.parent
    sdk = root / "sdk" / "aios_sdk.py"
    assert sdk.exists()
    assert sdk.stat().st_size > 0


def test_sdk_init_exists():
    root = Path(__file__).parent.parent
    init = root / "sdk" / "__init__.py"
    if init.exists():
        assert init.stat().st_size > 0
