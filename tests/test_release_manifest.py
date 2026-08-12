from __future__ import annotations

from scripts.generate_release_manifest import build_manifest


def test_release_manifest_has_immutable_commit_images_and_unit_hashes():
    manifest = build_manifest()
    assert len(str(manifest["git_commit"])) == 40
    assert len(str(manifest["git_tree"])) == 40
    assert manifest["production_images"]
    assert all("@sha256:" in image for image in manifest["production_images"])
    assert manifest["systemd_units_sha256"]
    assert all(
        len(value) == 64 for value in manifest["systemd_units_sha256"].values()
    )
