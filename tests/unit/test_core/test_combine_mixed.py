#!/usr/bin/env python3
"""
Test script to verify how _combine_shell_constructs handles mixed shell constructs and regular commands.
"""
import os
import logging
from panther.plugins.environments.network_environment.docker_compose.docker_compose import (
    DockerComposeEnvironment,
)
from panther.core.observer.management.event_manager import EventManager
from panther.plugins.environments.network_environment.docker_compose.config_schema import (
    DockerComposeConfig,
)

# Configure logging
logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("test_combine_mixed")


def run_test():
    # Create a minimal environment instance
    config = DockerComposeConfig()
    event_manager = EventManager()
    output_dir = "/tmp/panther_test_mixed"
    os.makedirs(output_dir, exist_ok=True)

    # Create environment
    env = DockerComposeEnvironment(
        env_config_to_test=config,
        output_dir=output_dir,
        env_type="network_environment",
        env_sub_type="docker_compose",
        event_manager=event_manager,
    )

    # Test cases with mixed content
    test_cases = [
        {
            "name": "Function followed by regular commands",
            "input": [
                "# Setup function",
                "setup_env() {",
                "  echo 'Setting up environment'",
                "  export PATH=$PATH:/usr/local/bin",
                "}",
                "# Call function",
                "setup_env",
                "echo 'Environment ready'",
            ],
        },
        {
            "name": "Multiple constructs mixed with regular commands",
            "input": [
                "echo 'Starting process'",
                "if [ -f config.json ]; then",
                "  source config.json",
                "fi",
                "echo 'Config loaded'",
                "for i in {1..3}; do",
                '  echo "Processing item $i"',
                "done",
                "echo 'All items processed'",
                "cleanup_data",
            ],
        },
        {
            "name": "Ternary operator-like command",
            "input": [
                "echo 'Starting cleanup'",
                "[ -d /opt/build ] && rm -rf /opt/build/* || mkdir -p /opt/build",
                "echo 'Cleanup finished'",
            ],
        },
        {
            "name": "Real-world case with IP functions and conditionals",
            "input": [
                'TARGET_IP=$(getent hosts target | tail -n 1 | awk "{ print \\$1 }");',
                'echo "Resolved target IP - $TARGET_IP" >> /app/logs/setup.log;',
                "ip_to_hex() {",
                '  echo $1 | awk -F"." "{ printf(\\"%02X%02X%02X%02X\\", \\$1, \\$2, \\$3, \\$4) }";',
                "}",
                "ip_to_decimal() {",
                '  echo $1 | awk -F"." "{ printf(\\"%.0f\\", (\\$1 * 256 * 256 * 256) + (\\$2 * 256 * 256) + (\\$3 * 256) + \\$4) }";',
                "}",
                "TARGET_IP_HEX=$(ip_to_decimal $TARGET_IP);",
                'echo "Resolved target IP in hex - $TARGET_IP_HEX" >> /app/logs/setup.log;',
                "if [ -d /opt/build ]; then",
                "  rm -rf /opt/build/*;",
                "else",
                "  mkdir -p /opt/build;",
                "fi",
            ],
        },
    ]

    for test_case in test_cases:
        name = test_case["name"]
        test_input = test_case["input"]

        logger.info("=" * 70)
        logger.info(f"Testing: {name}")
        logger.info("Input:")
        for i, cmd in enumerate(test_input):
            logger.info(f"[{i}] {repr(cmd)}")

        # Process with _combine_shell_constructs
        result = env._combine_shell_constructs(test_input)

        logger.info("-" * 70)
        logger.info("Output:")
        for i, cmd in enumerate(result):
            logger.info(f"[{i}] {repr(cmd)}")

        logger.info("=" * 70)
        logger.info(f"Input count: {len(test_input)}, Output count: {len(result)}")
        logger.info("Output command types:")

        # Count commands by type (single-line vs. multi-line)
        single_line = 0
        multi_line = 0
        for cmd in result:
            if "\n" in cmd:
                multi_line += 1
            else:
                single_line += 1

        logger.info(f"Single-line commands: {single_line}, Multi-line commands: {multi_line}")
        logger.info("-" * 70)


if __name__ == "__main__":
    run_test()
