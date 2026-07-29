#!/usr/bin/env python3
"""Run AIOS pure-Python web dashboard (NiceGUI)."""

from __future__ import annotations

import os
import sys


def main() -> int:
    # Ensure project root is on sys.path so aios_core.web_gui is importable
    project_root = os.path.dirname(os.path.abspath(__file__))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

    from aios_core.web_gui.main import run

    run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
