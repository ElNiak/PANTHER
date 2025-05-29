"""PANTHER documentation mkdocs tools.

This module contains mkdocs-related documentation tools.
"""

# Import key modules for easier access
from . import automate_mkdocs
from . import fix_encoding
from . import gen_ref_pages
from . import generate_plugin_docs
from . import mkdocs_all_import
from . import prepare_docs

# Define the public API
__all__ = [
    "automate_mkdocs",
    "fix_encoding",
    "gen_ref_pages",
    "generate_plugin_docs",
    "mkdocs_all_import",
    "prepare_docs",
]
