#!/usr/bin/env python3
"""Write a value-free immutable manifest for the deployed AIOS release."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_manifest() -> dict[str, object]:
    commit = subprocess.check_output(
        ["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True
    ).strip()
    tree = subprocess.check_output(
        ["git", "-C", str(ROOT), "rev-parse", "HEAD^{tree}"], text=True
    ).strip()
    compose = ROOT / "docker-compose.prod.yml"
    image_refs = sorted(
        match.group(1)
        for line in compose.read_text(encoding="utf-8").splitlines()
        if (match := re.match(r"\s*image:\s*([^\s#]+)", line))
    )
    images: list[str] = []
    for image in image_refs:
        if "@sha256:" in image:
            images.append(image)
            continue
        # Locally built production images have no registry tag in Compose, but
        # Docker still exposes a content-addressed RepoDigest/Image ID.
        details = json.loads(
            subprocess.check_output(["docker", "image", "inspect", image], text=True)
        )[0]
        digests = details.get("RepoDigests") or []
        if digests:
            images.append(str(digests[0]))
            continue
        image_id = str(details.get("Id") or "")
        if not image_id.startswith("sha256:"):
            raise RuntimeError(f"image has no immutable digest: {image}")
        repository = image.rsplit(":", 1)[0] if ":" in image.rsplit("/", 1)[-1] else image
        images.append(f"{repository}@{image_id}")
    images.sort()
    units = {
        str(path.relative_to(ROOT)): _sha(path)
        for path in sorted((ROOT / "deploy" / "systemd").rglob("*.service"))
    }
    units.update(
        {
            str(path.relative_to(ROOT)): _sha(path)
            for path in sorted((ROOT / "deploy" / "systemd").rglob("*.timer"))
        }
    )
    return {
        "version": 1,
        "created_at": time.time(),
        "git_commit": commit,
        "git_tree": tree,
        "production_images": images,
        "systemd_units_sha256": dict(sorted(units.items())),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    manifest = build_manifest()
    output = args.output or Path("/var/lib/aios/releases") / f"{manifest['git_commit']}.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=output.name + ".", dir=str(output.parent))
    temporary = Path(name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(manifest, handle, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary, 0o644)
        os.replace(temporary, output)
    finally:
        temporary.unlink(missing_ok=True)
    print(
        f"release_manifest=written commit={str(manifest['git_commit'])[:12]} "
        f"images={len(manifest['production_images'])}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
