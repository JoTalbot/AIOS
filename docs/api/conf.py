"""Sphinx configuration for AIOS API documentation."""

project = "AIOS"
author = "AIOS Development"
version = "2.1.1"
release = "2.1.1"

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
]

templates_path = ["_templates"]
exclude_patterns = ["_build"]
html_theme = "sphinx_rtd_theme"
