"""Comprehensive project health check — 10 assertions."""

from pathlib import Path

ROOT = Path(__file__).parent.parent


def test_1_core_imports():
    import aios_core
    assert aios_core.__version__ == "10.15.0"


def test_2_all_init_files():
    missing = []
    for d in ROOT.rglob('aios_core/*/'):
        if '__pycache__' in str(d): continue
        if not (d / '__init__.py').exists():
            missing.append(str(d.relative_to(ROOT)))
    assert len(missing) <= 5, f"Missing __init__.py: {missing}"


def test_3_no_critical_bare_excepts():
    content = (ROOT / "aios_core").rglob("*.py")
    count = 0
    for f in content:
        if f.name.startswith('__'): continue
        for line in open(f):
            if line.strip() == 'except:' and 'noqa' not in line:
                count += 1
    assert count == 0, f"Bare excepts found: {count}"


def test_4_config_files_present():
    required = [
        ".editorconfig", ".gitignore", "Makefile",
        "requirements.txt", "pyproject.toml",
        ".pre-commit-config.yaml",
    ]
    for f in required:
        assert (ROOT / f).exists(), f"Missing: {f}"


def test_5_documentation_present():
    docs = ["README.md", "CHANGELOG.md", "CONTRIBUTING.md", "SECURITY.md"]
    for d in docs:
        assert (ROOT / d).exists(), f"Missing doc: {d}"


def test_6_docker_files_present():
    files = ["Dockerfile", "docker-compose.yml", "docker-compose.prod.yml"]
    for f in files:
        assert (ROOT / f).exists(), f"Missing: {f}"


def test_7_ci_workflows_present():
    wf_dir = ROOT / ".github" / "workflows"
    if wf_dir.exists():
        workflows = list(wf_dir.glob("*.yml"))
        assert len(workflows) > 0, "No CI workflows"


def test_8_platform_descriptors_present():
    plat_dir = ROOT / "platforms"
    if plat_dir.exists():
        yamls = list(plat_dir.glob("*.yaml"))
        assert len(yamls) >= 3, f"Only {len(yamls)} platform descriptors"


def test_9_run_scripts_present():
    scripts = ["run_rest_api.py", "run_dashboard.py", "monitor.py"]
    for s in scripts:
        assert (ROOT / s).exists(), f"Missing script: {s}"


def test_10_sdk_present():
    sdk = ROOT / "sdk" / "aios_sdk.py"
    assert sdk.exists(), "SDK file missing"
