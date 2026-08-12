#!/usr/bin/env python3
"""Download private call audio using a runtime-only Google Drive manifest."""

from __future__ import annotations

import json
import logging
import os
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CALLS_DIR = Path(os.environ.get("AIOS_CALLS_DIR", str(REPO_ROOT / "Calls")))
DEFAULT_MANIFEST = "/srv/aios-private/Calls/.gdrive_audio_folders.json"
logger = logging.getLogger("aios.download_audio")


def load_audio_folders() -> list[tuple[str, str]]:
    """Load Drive folder IDs and private target labels outside the repository."""
    path = Path(os.environ.get("AIOS_GDRIVE_AUDIO_MANIFEST", DEFAULT_MANIFEST))
    value = json.loads(path.read_text(encoding="utf-8"))
    folders = value.get("folders") if isinstance(value, dict) else None
    if not isinstance(folders, list):
        raise ValueError("audio manifest must contain a folders list")
    result: list[tuple[str, str]] = []
    for item in folders:
        if not isinstance(item, dict):
            raise ValueError("each audio manifest entry must be an object")
        folder_id = str(item.get("id", "")).strip()
        target = str(item.get("target", "")).strip()
        if not re.fullmatch(r"[A-Za-z0-9_-]{10,}", folder_id) or not target:
            raise ValueError("audio manifest entry has an invalid id or target")
        result.append((folder_id, target))
    return result


def download_all_audio() -> None:
    import gdown

    CALLS_DIR.mkdir(parents=True, exist_ok=True)
    count = 0
    for folder_id, target_label in load_audio_folders():
        target_dir = CALLS_DIR / target_label
        target_dir.mkdir(parents=True, exist_ok=True)
        url = f"https://drive.google.com/drive/folders/{folder_id}"
        logger.info("Downloading private audio folder into %s", target_dir)
        try:
            gdown.download_folder(url=url, output=str(target_dir), quiet=True)
            audio_files = list(target_dir.glob("*.m4a")) + list(target_dir.glob("*.wav"))
            logger.info("Downloaded %d audio files", len(audio_files))
            count += len(audio_files)
        except Exception as exc:
            logger.warning("Audio folder download failed: %s", exc)
    logger.info("Downloaded %d call audio files in total", count)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    download_all_audio()
