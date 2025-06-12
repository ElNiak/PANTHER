#!/usr/bin/env python3
"""
Test script that specifically focuses on commands after constructs.
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
logger = logging.getLogger("test_after_construct")


def run_test():
    # Create a minimal environment instance
    config = DockerComposeConfig()
    event_manager = EventManager()
    output_dir = "/tmp/panther_test_after"
    os.makedirs(output_dir, exist_ok=True)

    # Create environment
    env = DockerComposeEnvironment(
        env_config_to_test=config,
        output_dir=output_dir,
        env_type="network_environment",
        env_sub_type="docker_compose",
        event_manager=event_manager,
    )

    # This is the example from your question
    original_input = [
        'TARGET_IP=$(getent hosts target | tail -n 1 | awk "{ print \\$1 }");',
        'echo "Resolved target IP - $TARGET_IP" >> /app/logs/setup.log;',
        'IVY_IP=$(hostname -I | awk "{ print \\$1 }" | head -n 1);',
        'echo "Resolved IP - $IVY_IP" >> /app/logs/setup.log;',
        " ",
        "ip_to_hex() {",
        '  echo $1 | awk -F"." "{ printf(\\"%02X%02X%02X%02X\\", \\$1, \\$2, \\$3, \\$4) }";',
        "}",
        " ",
        "ip_to_decimal() {",
        '  echo $1 | awk -F"." "{ printf(\\"%.0f\\", (\\$1 * 256 * 256 * 256) + (\\$2 * 256 * 256) + (\\$3 * 256) + \\$4) }";',
        "}",
        " ",
        "TARGET_IP_HEX=$(ip_to_decimal $TARGET_IP);",
        "IVY_IP_HEX=$(ip_to_decimal $IVY_IP);",
        'echo "Resolved target IP in hex - $TARGET_IP_HEX" >> /app/logs/setup.log;',
        'echo "Resolved IP in hex - $IVY_IP_HEX" >> /app/logs/setup.log;',
        " ",
        "rm -rf /opt/build/*;",
    ]

    logger.info("=" * 70)
    logger.info("Testing original input from question")
    logger.info("Input count: %d", len(original_input))

    # Process with _combine_shell_constructs
    result = env._combine_shell_constructs(original_input)

    logger.info("Output count: %d", len(result))
    logger.info("-" * 70)
    logger.info("Output commands:")
    for i, cmd in enumerate(result):
        if "\n" in cmd:
            logger.info(
                f"[{i}] MULTILINE: {repr(cmd.split()[0]+'...')} ({cmd.count(chr(10))+1} lines)"
            )
        else:
            logger.info(f"[{i}] SINGLE: {repr(cmd)}")

    # Create a more targeted test with specific constructs followed by commands
    test_cases = [
        {
            "name": "Function followed by single command",
            "input": ["my_func() {", "  echo 'inside func'", "}", "my_func"],
        },
        {
            "name": "Function followed by conditional",
            "input": [
                "my_func() {",
                "  echo 'inside func'",
                "}",
                "if [ -d /tmp ]; then",
                "  echo 'tmp exists'",
                "fi",
            ],
        },
    ]

    for test_case in test_cases:
        name = test_case["name"]
        test_input = test_case["input"]

        logger.info("=" * 70)
        logger.info(f"Testing: {name}")
        logger.info("Input count: %d", len(test_input))

        # Process with _combine_shell_constructs
        result = env._combine_shell_constructs(test_input)

        logger.info("Output count: %d", len(result))
        logger.info("-" * 70)
        logger.info("Output commands:")
        for i, cmd in enumerate(result):
            if "\n" in cmd:
                logger.info(
                    f"[{i}] MULTILINE: {repr(cmd.split()[0]+'...')} ({cmd.count(chr(10))+1} lines)"
                )
            else:
                logger.info(f"[{i}] SINGLE: {repr(cmd)}")


if __name__ == "__main__":
    run_test()
