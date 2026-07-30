from pathlib import Path
import importlib.util

SKILL_DIR = Path(__file__).resolve().parents[1]

def test_skill_contract_files_exist():
    assert (SKILL_DIR / "SKILL.md").exists()
    assert (SKILL_DIR / "code" / "run.py").exists()

def test_runtime_imports_callbacks():
    spec = importlib.util.spec_from_file_location("cb", "/opt/octopus-agent-callbacks.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    kb = mod.get_main_keyboard()
    assert len(kb["keyboard"]) >= 8
    assert callable(mod.handle_button)
    assert callable(mod.handle_callback)
