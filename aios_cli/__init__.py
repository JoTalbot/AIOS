"""AIOS CLI sub-commands — backward-compat re-exports."""

# Import from the sibling aios_cli.py file at project root
import importlib.util
import os

# The main CLI module is at PROJECT_ROOT/aios_cli.py (not inside this package)
_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_spec = importlib.util.spec_from_file_location("_aios_cli_main", os.path.join(_root, "aios_cli.py"))
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

main = _mod.main
