#!/usr/bin/env python3
"""
Test script to investigate issues with empty lines and conditional commands in _combine_shell_constructs.
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
logger = logging.getLogger("test_edge_cases")


def run_test():
    # Create a minimal environment instance
    config = DockerComposeConfig()
    event_manager = EventManager()
    output_dir = "/tmp/panther_test_edges"
    os.makedirs(output_dir, exist_ok=True)

    # Create environment
    env = DockerComposeEnvironment(
        env_config_to_test=config,
        output_dir=output_dir,
        env_type="network_environment",
        env_sub_type="docker_compose",
        event_manager=event_manager,
    )
    service_name = "test_service"
    service_targets = "test_target"
    protocol = type("Protocol", (), {"name": "test_protocol"})  # Mock protocol object
    service_config_to_test = type(
        "ServiceConfig",
        (),
        {
            "implementation": type(
                "Implementation", (), {"use_system_models": True}  # Mock implementation
            )
        },
    )  # Mock service config object
    service = type(
        "Service",
        (),
        {
            "service_name": service_name,
            "service_targets": service_targets,
            "service_config_to_test": service_config_to_test,
            "protocol": protocol,
        },
    )

    # Test edge cases
    test_cases = [
        {
            "name": "Multiple spaces between commands",
            "input": [
                "echo 'start'",
                " ",  # Empty space
                " ",  # Empty space
                "echo 'middle'",
                " ",  # Empty space
                "echo 'end'",
            ],
        },
        {
            "name": "Command with trailing spaces and blank lines",
            "input": [
                "for i in 1 2 3; do",
                "   echo $i",
                " ",  # Empty line within loop
                "   echo 'done with $i'",
                "done",
                " ",  # Empty line after loop
                " ",  # Another empty line
                "echo 'All done'",
            ],
        },
        {
            "name": "Function with blank lines",
            "input": [
                "my_func() {",
                " ",  # Empty line within function
                "  echo 'inside function'",
                " ",  # Empty line within function
                "  return 0",
                "}",
            ],
        },
        {
            "name": "Empty and None values mixed with constructs",
            "input": [
                "if [ $x -gt 10 ]; then",
                "",  # Empty string
                None,  # None value
                "  echo 'x is greater than 10'",
                "fi",
            ],
        },
        {
            "name": "Non-string values in command list",
            "input": [
                "echo 'start'",
                123,  # Non-string
                True,  # Boolean
                {"key": "value"},  # Dictionary
                "echo 'end'",
            ],
        },
        {
            "name": "IP resolution logging commands",
            "input": [
                "TARGET_IP=$(getent hosts "
                + service_targets
                + r' | tail -n 1 | awk "{ print \$1 }");',
                'echo "Resolved '
                + service_targets
                + ' IP - $TARGET_IP" >> /app/logs/ivy_setup.log;',
                r'IVY_IP=$(hostname -I | awk "{ print \$1 }" | head -n 1);',
                'echo "Resolved  '
                + service_name
                + ' IP - $IVY_IP" >> /app/logs/ivy_setup.log;',
                " ",
                "ip_to_hex() {",
                r'  echo $1 | awk -F"." "{ printf("%02X%02X%02X%02X", \$1, \$2, \$3, \$4) }";',
                "}",
                " ",
                "ip_to_decimal() {",
                r'  echo $1 | awk -F"." "{ printf("%.0f", (\$1 * 256 * 256 * 256) + (\$2 * 256 * 256) + (\$3 * 256) + \$4) }";',
                "}",
                " ",
                "TARGET_IP_HEX=$(ip_to_decimal $TARGET_IP);",
                "IVY_IP_HEX=$(ip_to_decimal $IVY_IP);",
                'echo "Resolved '
                + service_targets
                + ' IP in hex - $TARGET_IP_HEX" >> /app/logs/ivy_setup.log;',
                'echo "Resolved '
                + service_name
                + ' IP in hex - $IVY_IP_HEX" >> /app/logs/ivy_setup.log;',
                " ",
                (
                    "rm -rf /opt/panther_ivy/protocol-testing/apt/build/*;"
                    if service_config_to_test.implementation.use_system_models
                    else f"rm -rf /opt/panther_ivy/protocol-testing/{protocol.name}/build/*;"
                ),
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

        logger.info(f"Input count: {len(test_input)}, Output count: {len(result)}")
        if not result and any(
            cmd for cmd in test_input if isinstance(cmd, str) and cmd.strip()
        ):
            logger.warning("⚠️ Empty result returned despite valid commands in input!")


if __name__ in {"__main__", "__mp_main__"}:
    run_test()
