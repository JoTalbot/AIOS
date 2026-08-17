"""Repository contract for the reconciled Hetzner systemd inventory."""

from __future__ import annotations

from pathlib import Path

from scripts.audit_deployment_sources import OPTIONAL_NOT_INSTALLED_UNITS, repository_unit_inventory

ROOT = Path(__file__).resolve().parents[1]
SYSTEMD = ROOT / "deploy" / "systemd"


def _manifest_names(name: str) -> set[str]:
    return {
        line.strip()
        for line in (SYSTEMD / name).read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.startswith("#")
    }


def test_hetzner_installed_units_are_represented() -> None:
    installed = _manifest_names("HETZNER_INSTALLED_UNITS.txt")
    masks = _manifest_names("HETZNER_MASKED_UNITS.txt")
    inventory = repository_unit_inventory(ROOT)

    assert len(installed) == 164
    assert masks == {
        "aios-auto-coder.service",
        "aios-auto-promote.service",
        "aios-auto-promote.timer",
        "aios-groq-key.service",
    }
    assert installed <= inventory["represented_names"]
    assert inventory["represented_names"] >= OPTIONAL_NOT_INSTALLED_UNITS


def test_dropins_and_host_overrides_are_versioned() -> None:
    dropins = sorted(SYSTEMD.glob("aios-*.d/*.conf"))
    overrides = sorted((SYSTEMD / "host-overrides" / "hetzner").glob("*.service"))

    assert len(dropins) == 9
    assert {path.name for path in overrides} == {"aios-colab-keeper.service", "aios-olx-collector.service"}


def test_no_systemd_backup_files_are_tracked() -> None:
    inventory = repository_unit_inventory(ROOT)

    assert not any(".bak" in path for path in inventory["tracked_paths"])
    assert not any(path.endswith((".pem", ".key", ".p12", ".pfx")) for path in inventory["tracked_paths"])
