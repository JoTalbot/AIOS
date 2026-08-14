#!/usr/bin/env python3
"""Validate AIOS minimal, production-direct and locked dependency contracts."""

from __future__ import annotations

import argparse
import json
import re
import tomllib
from pathlib import Path
from typing import Any

from packaging.requirements import InvalidRequirement, Requirement
from packaging.utils import canonicalize_name
from packaging.version import InvalidVersion, Version


def _requirements(path: Path) -> tuple[dict[str, Requirement], list[str]]:
    parsed: dict[str, Requirement] = {}
    errors: list[str] = []
    for number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith(("#", "--", "-r ", "-c ")):
            continue
        try:
            requirement = Requirement(line)
        except InvalidRequirement as exc:
            errors.append(f"{path.name}:{number}: invalid requirement {line!r}: {exc}")
            continue
        name = canonicalize_name(requirement.name)
        if name in parsed:
            errors.append(f"{path.name}:{number}: duplicate direct requirement {name}")
        parsed[name] = requirement
    return parsed, errors


def _locked_requirements(path: Path) -> tuple[dict[str, Version], list[str]]:
    locked: dict[str, Version] = {}
    errors: list[str] = []
    exact_pin = re.compile(r"^([A-Za-z0-9_.-]+)==([^\s;]+)$")
    for number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith(("#", "--")):
            continue
        match = exact_pin.fullmatch(line)
        if not match:
            errors.append(f"{path.name}:{number}: lock entry is not an exact pin: {line!r}")
            continue
        name = canonicalize_name(match.group(1))
        try:
            version = Version(match.group(2))
        except InvalidVersion as exc:
            errors.append(f"{path.name}:{number}: invalid locked version: {exc}")
            continue
        if name in locked:
            errors.append(f"{path.name}:{number}: duplicate locked package {name}")
        locked[name] = version
    return locked, errors


def _project_dependencies(path: Path) -> tuple[dict[str, Requirement], list[str]]:
    document = tomllib.loads(path.read_text(encoding="utf-8"))
    dependencies = document.get("project", {}).get("dependencies", [])
    parsed: dict[str, Requirement] = {}
    errors: list[str] = []
    for raw in dependencies:
        try:
            requirement = Requirement(raw)
        except InvalidRequirement as exc:
            errors.append(f"pyproject.toml: invalid project dependency {raw!r}: {exc}")
            continue
        name = canonicalize_name(requirement.name)
        if name in parsed:
            errors.append(f"pyproject.toml: duplicate project dependency {name}")
        parsed[name] = requirement
    return parsed, errors


def dependency_contract(root: Path) -> dict[str, Any]:
    """Return dependency roles and all contract violations."""

    root = root.resolve()
    core, core_errors = _project_dependencies(root / "pyproject.toml")
    direct, direct_errors = _requirements(root / "requirements.txt")
    locked, lock_errors = _locked_requirements(root / "requirements.lock")
    errors = [*core_errors, *direct_errors, *lock_errors]

    missing_core_direct = sorted(core.keys() - direct.keys())
    missing_direct_lock = sorted(direct.keys() - locked.keys())
    if missing_core_direct:
        errors.append(f"minimal project dependencies missing from requirements.txt: {missing_core_direct}")
    if missing_direct_lock:
        errors.append(f"direct production dependencies missing from requirements.lock: {missing_direct_lock}")

    for source, requirements in (("pyproject.toml", core), ("requirements.txt", direct)):
        for name, requirement in requirements.items():
            version = locked.get(name)
            if (
                version is not None
                and requirement.specifier
                and not requirement.specifier.contains(version, prereleases=True)
            ):
                errors.append(f"locked {name}=={version} does not satisfy {source} constraint {requirement.specifier}")

    dockerfile = (root / "Dockerfile").read_text(encoding="utf-8")
    if "python -m pip install -r requirements.lock" not in dockerfile:
        errors.append("Dockerfile must install the exact requirements.lock")

    return {
        "root": str(root),
        "roles": {
            "pyproject.toml": "minimal-install-metadata",
            "requirements.txt": "full-production-direct-input",
            "requirements.lock": "exact-production-resolution",
            "pyproject.optional-dependencies.dev": "developer-tooling",
        },
        "counts": {"minimal": len(core), "direct": len(direct), "locked": len(locked)},
        "minimal_names": sorted(core),
        "direct_names": sorted(direct),
        "transitive_locked_count": len(locked.keys() - direct.keys()),
        "errors": errors,
    }


def _render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# AIOS dependency contract",
        "",
        f"- Minimal package dependencies: {report['counts']['minimal']}",
        f"- Full production direct dependencies: {report['counts']['direct']}",
        f"- Exact locked packages: {report['counts']['locked']}",
        f"- Locked transitive packages: {report['transitive_locked_count']}",
        f"- Contract errors: **{len(report['errors'])}**",
    ]
    lines.extend(f"- ERROR: {error}" for error in report["errors"])
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--strict", action="store_true", help="exit non-zero on contract errors")
    args = parser.parse_args()

    report = dependency_contract(args.root)
    print(json.dumps(report, indent=2, ensure_ascii=False) if args.json else _render_markdown(report), end="")
    return 1 if args.strict and report["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
