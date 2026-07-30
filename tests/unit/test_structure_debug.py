#!/usr/bin/env python3
"""Debug script to check actual GlobalConfig structure."""

import sys

sys.path.insert(
    0, "/Users/elniak/Documents/Project/Software-Engineer-AI-Agent-Atlas/REPOS/PANTHER"
)

from panther.config.core.models.global_config import (
    GlobalConfig,
    LoggingConfig,
    PathsConfig,
)


def check_structure():
    """Check the actual structure and field values."""
    print("=== Creating GlobalConfig ===")
    config = GlobalConfig()

    print(f"Version: {config.version}")
    print(f"Logging level: {config.logging.level}")
    print(f"Logging format: {config.logging.format}")
    print(f"Paths output_dir: {config.paths.output_dir}")
    print(f"Paths log_dir: {config.paths.log_dir}")
    print(f"Paths plugin_dir: {config.paths.plugin_dir}")

    print("\n=== Testing merge ===")
    base_config = GlobalConfig()
    override = {"paths": {"output_dir": "/merged/output"}}

    print(f"Before merge - log_dir: {base_config.paths.log_dir}")
    merged = base_config.merge(override)
    print(f"After merge - log_dir: {merged.paths.log_dir}")
    print(f"After merge - output_dir: {merged.paths.output_dir}")

    print("\n=== Checking all GlobalConfig fields ===")
    for field_name, field_info in GlobalConfig.model_fields.items():
        value = getattr(config, field_name)
        print(f"{field_name}: {type(value).__name__} = {repr(value)}")


if __name__ in {"__main__", "__mp_main__"}:
    check_structure()
