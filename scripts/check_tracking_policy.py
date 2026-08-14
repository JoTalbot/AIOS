#!/usr/bin/env python3
"""Validate that source/config files are tracked without exposing runtime data."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any

REQUIRED_TRACKED = {
    "deploy/monitoring/grafana-autonomy.json",
    "skills/stitch/design/.codex-plugin/plugin.json",
    "skills/stitch/design/plugin.json",
    "skills/stitch/design/skills/manage-design-system/examples/metadata.json",
    "skills/stitch/utilities/.codex-plugin/plugin.json",
    "skills/stitch/utilities/plugin.json",
}
REQUIRED_IGNORED_SAMPLES = {
    "backups/android_config/example.json",
    "backups/coder_backlog_20990101.json",
    "backups/inventory_before_clear_20990101.json",
    "backups/key_cleanup_20990101/.llm_keys.json",
    "backups/olx_published_archived_20990101.json",
    "catboost_info/catboost_training.json",
    "coverage.json",
    "docs/warehouse_pricelist.json",
    "data/runtime.json",
    "Calls/runtime.json",
    "android_companion/app/build/generated.json",
}
FORBIDDEN_TRACKED_BASENAMES = {".llm_keys.json", ".cards_vault.json", "secrets.env"}
FORBIDDEN_TRACKED_SUFFIXES = {".pem", ".p12", ".pfx"}


def _run(args: list[str], root: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=root, text=True, capture_output=True, check=False)


def _is_ignored(root: Path, path: str) -> bool:
    return _run(["git", "check-ignore", "--no-index", "-q", path], root).returncode == 0


def tracking_contract(root: Path) -> dict[str, Any]:
    """Return source-tracking invariants and violations."""

    root = root.resolve()
    ignore_lines = [
        line.strip()
        for line in (root / ".gitignore").read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    errors: list[str] = []
    if "*.json" in ignore_lines:
        errors.append("global *.json ignore is forbidden; classify mutable JSON by path")
    errors.extend(
        f"missing source build-directory exception: {required_rule}"
        for required_rule in ("!/skills/stitch/build/", "!/skills/stitch/build/**")
        if required_rule not in ignore_lines
    )

    tracked_result = _run(["git", "ls-files", "-z"], root)
    if tracked_result.returncode != 0:
        errors.append(tracked_result.stderr.strip() or "git ls-files failed")
        tracked: set[str] = set()
    else:
        tracked = {item for item in tracked_result.stdout.split("\0") if item}

    missing_required = sorted(REQUIRED_TRACKED - tracked)
    if missing_required:
        errors.append(f"required JSON manifests are not tracked: {missing_required}")

    stitch_build = sorted(path for path in tracked if path.startswith("skills/stitch/build/"))
    if len(stitch_build) < 41:
        errors.append(f"skills/stitch/build source is incomplete: tracked={len(stitch_build)}, expected>=41")

    still_ignored = sorted(path for path in REQUIRED_TRACKED if _is_ignored(root, path))
    if still_ignored:
        errors.append(f"required manifests still match ignore rules: {still_ignored}")
    if _is_ignored(root, "skills/stitch/build/plugin.json"):
        errors.append("skills/stitch/build source still matches a build/ ignore rule")

    missing_runtime_ignores = sorted(path for path in REQUIRED_IGNORED_SAMPLES if not _is_ignored(root, path))
    if missing_runtime_ignores:
        errors.append(f"runtime/sensitive samples are not ignored: {missing_runtime_ignores}")

    forbidden_tracked = sorted(
        path
        for path in tracked
        if Path(path).name in FORBIDDEN_TRACKED_BASENAMES
        or Path(path).suffix.lower() in FORBIDDEN_TRACKED_SUFFIXES
        or (Path(path).name == ".env" and path != ".env.example")
    )
    if forbidden_tracked:
        errors.append(f"sensitive paths are tracked: {forbidden_tracked}")

    return {
        "root": str(root),
        "tracked_files": len(tracked),
        "tracked_stitch_build_files": len(stitch_build),
        "required_json_manifests": len(REQUIRED_TRACKED),
        "runtime_ignore_samples": len(REQUIRED_IGNORED_SAMPLES),
        "errors": errors,
    }


def _render(report: dict[str, Any]) -> str:
    lines = [
        "# AIOS tracking policy",
        "",
        f"- Tracked files: {report['tracked_files']}",
        f"- Tracked Stitch build source files: {report['tracked_stitch_build_files']}",
        f"- Required JSON manifests: {report['required_json_manifests']}",
        f"- Runtime ignore samples: {report['runtime_ignore_samples']}",
        f"- Contract errors: **{len(report['errors'])}**",
    ]
    lines.extend(f"- ERROR: {error}" for error in report["errors"])
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()
    report = tracking_contract(args.root)
    print(json.dumps(report, ensure_ascii=False, indent=2) if args.json else _render(report), end="")
    return 1 if args.strict and report["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
