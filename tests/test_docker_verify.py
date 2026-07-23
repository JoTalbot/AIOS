"""Verify Docker and production files."""

from pathlib import Path


def test_dockerfile_has_from():
    root = Path(__file__).parent.parent
    content = (root / "Dockerfile").read_text()
    assert "FROM" in content


def test_docker_compose_has_services():
    root = Path(__file__).parent.parent
    content = (root / "docker-compose.yml").read_text()
    assert "services:" in content


def test_prod_compose_has_services():
    root = Path(__file__).parent.parent
    content = (root / "docker-compose.prod.yml").read_text()
    assert "services:" in content


def test_makefile_has_help():
    root = Path(__file__).parent.parent
    content = (root / "Makefile").read_text()
    assert "help:" in content
