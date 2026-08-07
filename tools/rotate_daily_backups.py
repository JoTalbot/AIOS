#!/usr/bin/env python3
"""Rotate daily backups — keep last N backup sets (by timestamp prefix)."""
import os
import re
from pathlib import Path
from collections import defaultdict

backup_dir = Path("/root/AIOS/backups/daily")
keep_sets = int(os.getenv("AIOS_BACKUP_KEEP_SETS", "7"))

if not backup_dir.exists():
    print(f"No dir {backup_dir}")
    exit(0)

# Group files by timestamp prefix YYYYMMDD_HHMMSS
pattern = re.compile(r"^(\d{8}_\d{6})__")
groups = defaultdict(list)
for f in backup_dir.iterdir():
    if f.is_file():
        m = pattern.match(f.name)
        if m:
            groups[m.group(1)].append(f)
        else:
            # fallback: by mtime
            groups["other"].append(f)

# Sort timestamps descending (newest first)
sorted_ts = sorted([k for k in groups.keys() if k != "other"], reverse=True)
keep_ts = set(sorted_ts[:keep_sets])
delete_ts = set(sorted_ts[keep_sets:])

total_freed = 0
deleted = 0
for ts in delete_ts:
    for f in groups[ts]:
        try:
            size = f.stat().st_size
            f.unlink()
            total_freed += size
            deleted += 1
            print(f"Deleted {f.name} ({size//1024}KB)")
        except Exception as e:
            print(f"Failed {f}: {e}")

# Also handle "other" group if too many
if "other" in groups and len(groups["other"]) > 20:
    others = sorted(groups["other"], key=lambda p: p.stat().st_mtime)
    for f in others[:-20]:
        try:
            size = f.stat().st_size
            f.unlink()
            total_freed += size
            deleted += 1
            print(f"Deleted other {f.name}")
        except Exception as e:
            print(f"Failed {f}: {e}")

print(f"Done: kept {len(keep_ts)} sets ({len(keep_ts)*7} files), deleted {deleted} files, freed {total_freed//(1024*1024)}MB")
# Print current
remaining = sorted([k for k in groups.keys() if k in keep_ts], reverse=True)
print(f"Kept timestamps: {remaining}")
