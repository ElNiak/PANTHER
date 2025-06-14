"""
Mutation Testing Configuration for PANTHER

This module sets up mutation testing to validate the quality of our test suite
by introducing small changes (mutations) to the code and checking if tests catch them.
"""

import os
import sys
from pathlib import Path

# Add PANTHER to Python path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Mutation testing configuration
MUTATION_CONFIG = {
    "target_modules": [
        "panther.core.event_system",
        "panther.core.command_processor",
        "panther.core.docker_builder",
        "panther.core.observer",
    ],
    "test_command": "pytest -x -q",
    "mutators": [
        "statement_deletion",
        "boolean_replacement",
        "comparison_replacement",
        "arithmetic_replacement",
        "assignment_replacement",
        "return_value_replacement",
    ],
    "exclude_patterns": [
        "**/test_*.py",
        "**/__pycache__/**",
        "**/templates/**",
    ],
    "timeout_factor": 2,
    "max_mutations_per_file": 50,
}

# Mutmut configuration file content
MUTMUT_CONFIG = """
[mutmut]
paths_to_mutate=panther/core/
backup=False
runner=python -m pytest -x -q
tests_dir=tests/unit/
dict_synonyms=Dict,OrderedDict,DefaultDict
"""


def setup_mutation_testing():
    """Set up mutation testing environment."""
    # Create .mutmut-cache directory
    cache_dir = Path(".mutmut-cache")
    cache_dir.mkdir(exist_ok=True)

    # Write mutmut config
    config_path = Path("setup.cfg")
    existing_content = ""

    if config_path.exists():
        existing_content = config_path.read_text()

    if "[mutmut]" not in existing_content:
        with open(config_path, "a") as f:
            f.write("\n" + MUTMUT_CONFIG)

    print("Mutation testing configuration complete.")
    print("Run 'mutmut run' to start mutation testing.")


if __name__ == "__main__":
    setup_mutation_testing()
