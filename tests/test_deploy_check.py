"""test_deploy_check test."""
from pathlib import Path
ROOT = Path(__file__).parent.parent
def test(): assert (ROOT / 'deploy').exists()
