"""AIOS observability package.

Contains observability submodules (metrics, tracing) plus re-exports the
legacy single-file facade ``aios_core/observability.py`` so that
``from aios_core.observability import Observability, MetricKind`` keeps working.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_FACADE = Path(__file__).resolve().parent.parent / "observability.py"
_SPEC = importlib.util.spec_from_file_location("aios_core.observability._facade", _FACADE)
_MOD = importlib.util.module_from_spec(_SPEC)
assert _SPEC and _SPEC.loader
sys.modules["aios_core.observability._facade"] = _MOD  # dataclasses inspect sys.modules
_SPEC.loader.exec_module(_MOD)

for _name in dir(_MOD):
    if not _name.startswith("_"):
        globals()[_name] = getattr(_MOD, _name)
del _name
