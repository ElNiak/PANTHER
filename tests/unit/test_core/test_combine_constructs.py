from typing import List

#!/usr/bin/env python3
"""
Test script to diagnose issues with the _combine_shell_constructs method.
"""
import logging
import os

from panther.core.observer.management.event_manager import EventManager
from panther.plugins.environments.network_environment.docker_compose.config_schema import (
    DockerComposeConfig,
)
from panther.plugins.environments.network_environment.docker_compose.docker_compose import (
    DockerComposeEnvironment,
)

# Configure logging
logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("test_combine_constructs")


# Create a minimal environment instance to access the _combine_shell_constructs method
def create_test_env():
    config = DockerComposeConfig()
    event_manager = EventManager()
    output_dir = "/tmp/panther_test"
    os.makedirs(output_dir, exist_ok=True)

    # Create a test environment
    env = DockerComposeEnvironment(
        env_config_to_test=config,
        output_dir=output_dir,
        env_type="network_environment",
        env_sub_type="docker_compose",
        event_manager=event_manager,
    )
    return env


# Test cases for the _combine_shell_constructs method
def run_test_cases():
    env = create_test_env()

    # Test case 1: Basic loop construct
    test_case_1 = ["for i in 1 2 3; do", 'echo "Loop $i"', "done"]

    # Test case 2: Function definition
    test_case_2 = ["my_function() {", 'echo "Inside function"', "return 0", "}"]

    # Test case 3: If statement
    test_case_3 = [
        "if [ -f /etc/hosts ]; then",
        'echo "Host file exists"',
        "else",
        'echo "No host file found"',
        "fi",
    ]

    # Test case 4: Nested constructs
    test_case_4 = [
        "for file in *.txt; do",
        'if [ -s "$file" ]; then',
        'echo "Processing $file"',
        "cat $file | grep pattern",
        "fi",
        "done",
    ]

    # Test case 5: Empty list
    test_case_5 = []

    # Test case 6: List with empty or non-string elements
    test_case_6 = ["command1", "", None, 123, "command2"]

    # Test case 7: Incomplete construct (should trigger warning)
    test_case_7 = ["for i in 1 2 3; do", 'echo "No end to this loop"']

    # Test case 8: While loop with indentation
    test_case_8 = [
        "while [ ! -f /app/sync_logs/ivy_ready.log ]; do",
        '\techo "Waiting for Ivy testers to be ready..." >> /app/logs/tester_ready.log;',
        "\tsleep 2;",
        "done;",
    ]

    # Run all test cases
    test_cases = [
        ("Basic loop", test_case_1),
        ("Function definition", test_case_2),
        ("If statement", test_case_3),
        ("Nested constructs", test_case_4),
        ("Empty list", test_case_5),
        ("Mixed content list", test_case_6),
        ("Incomplete construct", test_case_7),
        ("While loop with indentation", test_case_8),
    ]

    for name, test_case in test_cases:
        logger.info(f"Testing: {name}")
        logger.info(f"Input: {test_case}")
        result = env._combine_shell_constructs(test_case)
        logger.info(f"Result: {result}")
        logger.info("-" * 50)


if __name__ == "__main__":
    run_test_cases()
