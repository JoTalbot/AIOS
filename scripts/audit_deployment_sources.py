#!/usr/bin/env python3
"""Read-only audit of AIOS deployment sources and optional host drift.

The repository audit is safe in CI. Runtime inspection only reads systemd and
Docker metadata; it never changes, reloads, restarts, enables or removes units.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

import yaml

CANONICAL_COMPOSE = "docker-compose.prod.yml"
COMPOSE_ROLES = {
    "docker-compose.prod.yml": "canonical-production",
    "docker-compose.yml": "local-integration",
    "docker-compose.unified.yml": "experimental-swarm-ui",
    "deploy/production/docker-compose.prod.yml": "legacy-v9-reference-only",
}
REQUIRED_PRODUCTION_SERVICES = {
    "aios-api",
    "aios-mcp",
    "aios-dashboard",
    "prometheus",
    "grafana",
    "alertmanager",
}


def _run(args: list[str], *, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=cwd, text=True, capture_output=True, check=False)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _compose_summary(root: Path, relative_path: str) -> dict[str, Any]:
    path = root / relative_path
    summary: dict[str, Any] = {
        "path": relative_path,
        "role": COMPOSE_ROLES[relative_path],
        "exists": path.is_file(),
        "sha256": None,
        "services": [],
        "error": None,
    }
    if not path.is_file():
        return summary
    try:
        document = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        services = document.get("services") or {}
        if not isinstance(services, dict):
            raise TypeError("top-level services must be a mapping")
        summary["services"] = sorted(services)
        summary["sha256"] = _sha256(path)
    except (OSError, TypeError, yaml.YAMLError) as exc:
        summary["error"] = f"{type(exc).__name__}: {exc}"
    return summary


def repository_audit(root: Path) -> dict[str, Any]:
    """Return the static deployment contract and repository violations."""

    root = root.resolve()
    variants = {path: _compose_summary(root, path) for path in COMPOSE_ROLES}
    errors: list[str] = []
    warnings: list[str] = []

    for path, summary in variants.items():
        if not summary["exists"]:
            errors.append(f"missing declared Compose source: {path}")
        elif summary["error"]:
            errors.append(f"invalid Compose source {path}: {summary['error']}")

    canonical = variants[CANONICAL_COMPOSE]
    missing_services = REQUIRED_PRODUCTION_SERVICES - set(canonical["services"])
    if missing_services:
        errors.append(f"canonical Compose misses required services: {sorted(missing_services)}")

    legacy = variants["deploy/production/docker-compose.prod.yml"]
    if canonical["sha256"] and legacy["sha256"] and canonical["sha256"] != legacy["sha256"]:
        warnings.append(
            "legacy deploy/production/docker-compose.prod.yml differs from the canonical root file; do not deploy it"
        )

    deployment_contract = root / "deploy/DEPLOYMENT_SOURCES.md"
    if not deployment_contract.is_file():
        errors.append("missing deployment source-of-truth document: deploy/DEPLOYMENT_SOURCES.md")

    deploy_workflow_path = root / ".github/workflows/deploy.yml"
    deploy_workflow = deploy_workflow_path.read_text(encoding="utf-8")
    header = deploy_workflow.split("jobs:", 1)[0]
    if "workflow_dispatch:" not in header or "push:" in header:
        errors.append("deploy.yml must remain manual-only (workflow_dispatch, no push trigger)")
    required_commands = (
        "docker compose -f docker-compose.prod.yml pull",
        "docker compose -f docker-compose.prod.yml up -d",
    )
    errors.extend(
        f"deploy.yml does not use canonical command: {command}"
        for command in required_commands
        if command not in deploy_workflow
    )

    all_in_one = (root / "deploy-all-in-one.sh").read_text(encoding="utf-8")
    if "LOCAL/DEMO ONLY" not in all_in_one or "docker compose -f docker-compose.yml" not in all_in_one:
        errors.append("deploy-all-in-one.sh must explicitly identify and select the local Compose stack")

    swarm = (root / "scripts/deploy_swarm.sh").read_text(encoding="utf-8")
    if "AIOS_ALLOW_EXPERIMENTAL_SWARM" not in swarm:
        errors.append("experimental swarm deployment must require an explicit opt-in")

    return {
        "root": str(root),
        "canonical_compose": CANONICAL_COMPOSE,
        "compose_variants": variants,
        "errors": errors,
        "warnings": warnings,
    }


def _tracked_unit_names(root: Path) -> set[str]:
    result = _run(["git", "ls-files", "*.service", "*.timer"], cwd=root)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "git ls-files failed")
    return {
        Path(line).name
        for line in result.stdout.splitlines()
        if line and "/disabled/" not in line and Path(line).name.startswith("aios-")
    }


def _installed_unit_names(root: Path) -> set[str]:
    result = _run(["systemctl", "list-unit-files", "--no-legend", "--no-pager"], cwd=root)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "systemctl list-unit-files failed")
    names = set()
    for line in result.stdout.splitlines():
        columns = line.split()
        if columns and columns[0].startswith("aios-") and columns[0].endswith((".service", ".timer")):
            names.add(columns[0])
    return names


def _container_compose_sources(root: Path) -> dict[str, str]:
    listed = _run(["docker", "ps", "--format", "{{.Names}}"], cwd=root)
    if listed.returncode != 0:
        raise RuntimeError(listed.stderr.strip() or "docker ps failed")
    sources: dict[str, str] = {}
    for name in sorted(line for line in listed.stdout.splitlines() if line.startswith("aios-")):
        inspected = _run(
            [
                "docker",
                "inspect",
                "-f",
                '{{ index .Config.Labels "com.docker.compose.project.config_files" }}',
                name,
            ],
            cwd=root,
        )
        if inspected.returncode == 0:
            source = inspected.stdout.strip()
            if source:
                sources[name] = source
    return sources


def runtime_audit(root: Path) -> dict[str, Any]:
    """Read systemd and Docker metadata without mutating the host."""

    tracked = _tracked_unit_names(root)
    installed = _installed_unit_names(root)
    container_sources = _container_compose_sources(root)
    unexpected_sources = {
        name: source
        for name, source in container_sources.items()
        if Path(source.split(",", 1)[0]).name != CANONICAL_COMPOSE or "/deploy/production/" in source.replace("\\", "/")
    }
    return {
        "tracked_aios_units": sorted(tracked),
        "installed_aios_units": sorted(installed),
        "installed_not_tracked": sorted(installed - tracked),
        "tracked_not_installed": sorted(tracked - installed),
        "container_compose_sources": container_sources,
        "containers_using_unexpected_source": unexpected_sources,
    }


def _render_markdown(report: dict[str, Any]) -> str:
    lines = ["# AIOS deployment audit", "", f"Canonical Compose: `{report['canonical_compose']}`", ""]
    lines.append("## Compose variants")
    lines.extend(
        f"- `{item['path']}` — **{item['role']}**, services={len(item['services'])}, "
        f"valid={'yes' if item['exists'] and not item['error'] else 'no'}"
        for item in report["compose_variants"].values()
    )
    lines.extend(["", f"Repository errors: **{len(report['errors'])}**"])
    lines.extend(f"- ERROR: {error}" for error in report["errors"])
    lines.extend(f"- WARNING: {warning}" for warning in report["warnings"])
    runtime = report.get("runtime")
    if runtime:
        lines.extend(
            [
                "",
                "## Runtime drift (read-only)",
                f"- Tracked AIOS unit names: {len(runtime['tracked_aios_units'])}",
                f"- Installed AIOS unit names: {len(runtime['installed_aios_units'])}",
                f"- Installed but not tracked: {len(runtime['installed_not_tracked'])}",
                f"- Tracked but not installed: {len(runtime['tracked_not_installed'])}",
                f"- Containers using unexpected Compose source: {len(runtime['containers_using_unexpected_source'])}",
            ]
        )
        if runtime["installed_not_tracked"]:
            lines.append(
                "- Unmanaged installed units: " + ", ".join(f"`{x}`" for x in runtime["installed_not_tracked"])
            )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--runtime", action="store_true", help="also inspect systemd and Docker metadata read-only")
    parser.add_argument("--json", action="store_true", help="emit JSON instead of Markdown")
    parser.add_argument("--strict", action="store_true", help="exit non-zero on repository contract errors")
    parser.add_argument(
        "--fail-on-runtime-drift",
        action="store_true",
        help="also fail when installed/tracked units or container Compose sources drift",
    )
    args = parser.parse_args()

    report = repository_audit(args.root)
    if args.runtime:
        try:
            report["runtime"] = runtime_audit(args.root.resolve())
        except (OSError, RuntimeError) as exc:
            report["runtime_error"] = f"{type(exc).__name__}: {exc}"

    print(json.dumps(report, indent=2, ensure_ascii=False) if args.json else _render_markdown(report), end="")

    failed = bool(args.strict and report["errors"])
    if args.fail_on_runtime_drift:
        runtime = report.get("runtime")
        failed = (
            failed
            or not runtime
            or bool(
                runtime["installed_not_tracked"]
                or runtime["tracked_not_installed"]
                or runtime["containers_using_unexpected_source"]
            )
        )
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
