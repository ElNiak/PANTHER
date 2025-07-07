"""PANTHER documentation mkdocs tools.

This module contains mkdocs-related documentation tools.
"""

# Import key modules for easier access
from . import (
    automate_mkdocs,
    fix_encoding,
    gen_ref_pages,
    generate_plugin_docs,
    mkdocs_all_import,
    prepare_docs,
)

# Define the public API
__all__ = [
    "automate_mkdocs",
    "fix_encoding",
    "gen_ref_pages",
    "generate_plugin_docs",
    "mkdocs_all_import",
    "prepare_docs",
]
