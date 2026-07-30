import importlib.util, json
from pathlib import Path
P=Path('/root/agents/-Octopus/skills/core/money-earner-orchestrator/code/skill_index_rebuilder.py')
s=importlib.util.spec_from_file_location('rebuilder',P); m=importlib.util.module_from_spec(s); s.loader.exec_module(m)
def test_build_matches_current_index():
    fresh=m.build(); current=json.loads(m.INDEX.read_text())
    assert m.normalized(fresh)==m.normalized(current)
def test_no_duplicates_and_paths_exist():
    fresh=m.build(); assert fresh['audit']['duplicate_count']==0
    assert fresh['audit']['total']==fresh['audit']['unique_names']
    assert all(Path(x['path']).exists() for x in fresh['skills'].values())
def test_archived_skill_not_indexed():
    fresh=m.build(); assert 'core/skill-marketplace-sync' not in fresh['skills']
    assert fresh['skills_by_name']['skill-marketplace-sync']==['meta/skill-marketplace-sync']
