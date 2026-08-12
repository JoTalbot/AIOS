#!/usr/bin/env python3
"""Render Alertmanager config from a public template and credential metadata."""

from __future__ import annotations

import argparse
import os
import tempfile
from pathlib import Path

ROOT = Path(os.environ.get("AIOS_ROOT", str(Path(__file__).resolve().parents[1])))


def render(template: Path, owner_chat_file: Path, output: Path) -> None:
    owner = owner_chat_file.read_text(encoding="utf-8").strip()
    try:
        int(owner)
    except ValueError as exc:
        raise RuntimeError("Telegram owner chat credential is invalid") from exc
    value = template.read_text(encoding="utf-8")
    marker = "__TELEGRAM_OWNER_CHAT_ID__"
    if value.count(marker) != 1:
        raise RuntimeError("Alertmanager template owner marker is missing or duplicated")
    rendered = value.replace(marker, owner)
    output.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=output.name + ".", dir=str(output.parent))
    tmp = Path(name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(rendered)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(tmp, 0o600)
        os.replace(tmp, output)
    finally:
        tmp.unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--template",
        type=Path,
        default=ROOT / "deploy/monitoring/alertmanager/alertmanager.yml.tmpl",
    )
    parser.add_argument(
        "--owner-chat-file",
        type=Path,
        default=Path("/etc/aios/credentials/telegram_owner_chat_id"),
    )
    parser.add_argument(
        "--output", type=Path, default=Path("/etc/aios/alertmanager.yml")
    )
    args = parser.parse_args()
    render(args.template, args.owner_chat_file, args.output)
    print("alertmanager_config=rendered")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
