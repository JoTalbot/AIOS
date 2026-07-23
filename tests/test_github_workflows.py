"""Tests for GitHub workflow files existence."""

import os
from pathlib import Path


def test_ci_workflow_exists():
    root = Path(__file__).parent.parent
    wf = root / '.github' / 'workflows' / 'ci.yml'
    assert wf.exists(), 'CI workflow missing'


def test_docs_workflow_exists():
    root = Path(__file__).parent.parent
    wf = root / '.github' / 'workflows' / 'docs.yml'
    assert wf.exists(), 'Docs workflow missing'
