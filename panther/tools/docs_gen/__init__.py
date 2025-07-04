# PANTHER Documentation Generation Tools
"""
Automated documentation generation tools for PANTHER project.

This package provides:
- discover_sources.py: Automated README discovery and analysis
- generate_build_mapping.py: Integration module for panther_builder.py
- INTEGRATION_INSTRUCTIONS.md: Complete integration guide

Phase 1 Implementation: Replaces manual 85+ line build_dict with automated discovery.
"""

__version__ = "1.0.0"
__author__ = "ATLAS"

# Make key functions available at package level
try:
    from .discover_sources import PantherSourceDiscovery
    from .generate_build_mapping import get_automated_build_dict, get_build_dict

    __all__ = ["get_automated_build_dict", "get_build_dict", "PantherSourceDiscovery"]
except ImportError:
    # Graceful fallback if dependencies are missing
    __all__ = []
