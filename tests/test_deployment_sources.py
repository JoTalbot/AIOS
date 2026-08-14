"""Contract tests for the documented AIOS deployment source of truth."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from scripts.audit_deployment_sources import CANONICAL_COMPOSE, repository_audit

ROOT = Path(__file__).resolve().parents[1]


def test_repository_deployment_contract_is_consistent() -> None:
    report = repository_audit(ROOT)

    assert report["errors"] == []
    assert report["canonical_compose"] == "docker-compose.prod.yml"
    assert report["compose_variants"][CANONICAL_COMPOSE]["role"] == "canonical-production"
    assert report["compose_variants"]["docker-compose.yml"]["role"] == "local-integration"
    assert report["compose_variants"]["docker-compose.unified.yml"]["role"] == "experimental-swarm-ui"
    assert report["compose_variants"]["deploy/production/docker-compose.prod.yml"]["role"].startswith("legacy-")


def test_canonical_compose_has_production_control_plane() -> None:
    report = repository_audit(ROOT)
    services = set(report["compose_variants"][CANONICAL_COMPOSE]["services"])

    assert {"aios-api", "aios-mcp", "aios-dashboard"} <= services
    assert {"prometheus", "grafana", "alertmanager"} <= services


def test_deployment_audit_cli_strict_mode() -> None:
    result = subprocess.run(
        [sys.executable, "scripts/audit_deployment_sources.py", "--strict"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "Canonical Compose: `docker-compose.prod.yml`" in result.stdout
    assert "Repository errors: **0**" in result.stdout
