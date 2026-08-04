#!/usr/bin/env python3
"""CLI for no-action workflow readiness report."""
from __future__ import annotations

import json
from pathlib import Path

from aios_core.phone_workflow_readiness import PhoneWorkflowReadiness

ROOT = Path(__file__).resolve().parent

if __name__ == "__main__":
    print(json.dumps(PhoneWorkflowReadiness(ROOT).snapshot(), ensure_ascii=False, indent=2))
