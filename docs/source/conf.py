# Configuration file for the Sphinx documentation builder.
# AIOS Documentation — v9.3.0

import os
import sys

sys.path.insert(0, os.path.abspath("../../"))

# -- Project information -------------------------------------------------------
project = "AIOS — Autonomous Intelligence Operating System"
copyright = "2026, JoTalbot & AIOS Core Team"
author = "JoTalbot"
release = "9.2.0"
version = "9.2.0"

# -- General configuration -----------------------------------------------------
extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
    "sphinx.ext.intersphinx",
    "sphinx.ext.todo",
    "sphinx.ext.coverage",
    "sphinx.ext.ifconfig",
]

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

# -- Options for HTML output ---------------------------------------------------
html_theme = "sphinx_rtd_theme"
html_static_path = ["_static"]
html_theme_options = {
    "navigation_depth": 4,
    "collapse_navigation": False,
    "sticky_navigation": True,
    "includehidden": True,
    "titles_only": False,
    "display_version": True,
    "prev_next_buttons_location": "both",
    "logo_only": False,
}
html_logo = None
html_favicon = None

# -- Extension configuration ---------------------------------------------------
autodoc_default_options = {
    "members": True,
    "member-order": "bysource",
    "undoc-members": True,
    "show-inheritance": True,
}
autodoc_mock_imports = [
    "starlette",
    "uvicorn",
    "httpx",
    "psutil",
    "aiohttp",
    "pydantic",
    "fastapi",
]

napoleon_google_docstring = True
napoleon_numpy_docstring = True
napoleon_include_init_with_doc = True
napoleon_use_param = True
napoleon_use_rtype = True

intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
}

todo_emit_warnings = False

# -- Options for LaTeX/PDF output ----------------------------------------------
latex_elements = {
    "papersize": "a4paper",
    "pointsize": "11pt",
    "preamble": r"""
\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage{ DejaVuSans}
""",
}
latex_documents = [
    ("index", "AIOS.tex", "AIOS Documentation", "JoTalbot", "manual"),
]

# -- Options for manual page output --------------------------------------------
man_pages = [
    ("index", "aios", "AIOS Documentation", [author], 1),
]
