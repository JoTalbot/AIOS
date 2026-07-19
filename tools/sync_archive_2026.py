#!/usr/bin/env python3
"""Sync the living layer-4 (2026 Archive) docs into docs/aios/.

Layer 4 is the actively developed source. When a new version of
``AIOS_Archive_2026`` is unpacked, run this to refresh the matching layer
folders in ``docs/aios/`` while leaving all other layers (core, exec_layer,
docs, plans, qa, meta, constitution) untouched.

Usage:
    python3 tools/sync_archive_2026.py <path-to-extracted-AIOS_Archive_2026>
"""

import os
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEST = os.path.join(ROOT, "docs", "aios")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    src_root = sys.argv[1]
    # Archive layout: <root>/AIOS_Archive_2026/<layer>/<files>.md
    archive = None
    for name in ("AIOS_Archive_2026", "aios_archive_2026"):
        cand = os.path.join(src_root, name)
        if os.path.isdir(cand):
            archive = cand
            break
    if archive is None:
        archive = src_root  # allow passing the inner folder directly

    if not os.path.isdir(archive):
        print("Source not found: %s" % archive)
        return 1

    updated = 0
    for layer in sorted(os.listdir(archive)):
        src_layer = os.path.join(archive, layer)
        if not os.path.isdir(src_layer):
            continue
        dst_layer = os.path.join(DEST, layer)
        os.makedirs(dst_layer, exist_ok=True)
        for fn in os.listdir(src_layer):
            if not fn.endswith(".md"):
                continue
            shutil.copy2(os.path.join(src_layer, fn), os.path.join(dst_layer, fn))
            updated += 1
    print("Synced %d layer-4 docs into %s" % (updated, DEST))
    return 0


if __name__ == "__main__":
    sys.exit(main())
