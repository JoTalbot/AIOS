"""Deployment readiness smoke tests — version, config, Dockerfile."""

import os


def test_dockerfile_exists():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    dockerfile = os.path.join(root, "Dockerfile")
    assert os.path.exists(dockerfile), "Dockerfile missing"


def test_requirements_exists():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    req = os.path.join(root, "requirements.txt")
    assert os.path.exists(req), "requirements.txt missing"


def test_makefile_exists():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    mf = os.path.join(root, "Makefile")
    assert os.path.exists(mf), "Makefile missing"


def test_pyproject_exists():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    pp = os.path.join(root, "pyproject.toml")
    assert os.path.exists(pp), "pyproject.toml missing"
