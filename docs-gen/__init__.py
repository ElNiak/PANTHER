"""PANTHER documentation generation tools.

This package contains tools for generating and maintaining PANTHER's documentation.
"""

# Import key modules for easier access
from . import add_cross_references
from . import enhance_mkdocs_config
from . import fix_mkdocs_yaml
from . import generate_plugin_inventory
from . import pre_commit_docs
from . import update_init_files
from . import update_mkdocs_nav
from . import validate_documentation
from . import verify_docs
from . import verify_links

# Define the public API
__all__ = [
    "add_cross_references",
    "enhance_mkdocs_config",
    "fix_mkdocs_yaml",
    "generate_plugin_inventory",
    "pre_commit_docs",
    "update_init_files",
    "update_mkdocs_nav",
    "validate_documentation",
    "verify_docs",
    "verify_links"
]