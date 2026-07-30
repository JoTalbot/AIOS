from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parents[1]


def test_skill_contract_files_exist():
    assert (SKILL_DIR / 'SKILL.md').exists()
    assert (SKILL_DIR / 'code' / 'run.py').exists()


def test_skill_has_algorithm_and_control_section():
    text = (SKILL_DIR / 'SKILL.md').read_text(encoding='utf-8', errors='replace')
    assert '## Алгоритм' in text
    assert '## Контроль и развитие' in text
