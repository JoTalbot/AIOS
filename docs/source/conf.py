# Configuration file for the Sphinx documentation builder.

import os
import sys
sys.path.insert(0, os.path.abspath('../../'))

project = 'AIOS - Autonomous Intelligence Operating System'
copyright = '2026, JoTalbot & AIOS Core Team'
author = 'JoTalbot'
release = '9.0.0-alpha'

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.napoleon',
    'sphinx.ext.viewcode',
]

templates_path = ['_templates']
exclude_patterns = []

html_theme = 'sphinx_rtd_theme'
html_static_path = ['_static']
