#!/usr/bin/env python3
"""
Test script to debug how results from _combine_shell_constructs are processed in generate_entrypoint_with_structured_args.
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
logger = logging.getLogger("test_full_process")


class MockServiceManager:
    def __init__(self):
        self.service_name = "mock-service"
        self.service_targets = "target-service"
        self.service_config_to_test = type(
            "obj",
            (object,),
            {
                "implementation": type("obj", (object,), {"use_system_models": True}),
                "timeout": 60,
            },
        )
        self.protocol = type("obj", (object,), {"name": "mock-protocol"})

        # Create run_cmd dict with problematic test case
        self.run_cmd = {
            "setup_cmds": [
                "TARGET_IP=$(getent hosts "
                + self.service_targets
                + r' | tail -n 1 | awk "{ print \$1 }");',
                'echo "Resolved '
                + self.service_targets
                + ' IP - $TARGET_IP" >> /app/logs/ivy_setup.log;',
                r'IVY_IP=$(hostname -I | awk "{ print \$1 }" | head -n 1);',
                'echo "Resolved  '
                + self.service_name
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
                + self.service_targets
                + ' IP in hex - $TARGET_IP_HEX" >> /app/logs/ivy_setup.log;',
                'echo "Resolved '
                + self.service_name
                + ' IP in hex - $IVY_IP_HEX" >> /app/logs/ivy_setup.log;',
                " ",
                (
                    "rm -rf /opt/panther_ivy/protocol-testing/apt/build/*;"
                    if True
                    else f"rm -rf /opt/panther_ivy/protocol-testing/{self.protocol.name}/build/*;"
                ),
            ]
        }
        self.environments = {}
        self.volumes = []


def run_test():
    # Create a minimal environment instance
    config = DockerComposeConfig()
    event_manager = EventManager()
    output_dir = "/tmp/panther_test_full"
    os.makedirs(output_dir, exist_ok=True)

    # Create environment
    env = DockerComposeEnvironment(
        env_config_to_test=config,
        output_dir=output_dir,
        env_type="network_environment",
        env_sub_type="docker_compose",
        event_manager=event_manager,
    )

    # Create a mock service manager
    service = MockServiceManager()

    # First test just the combine function
    logger.info("=" * 70)
    logger.info("Testing _combine_shell_constructs directly:")

    cmds = service.run_cmd["setup_cmds"]
    logger.info(f"Input command count: {len(cmds)}")

    combined_cmds = env._combine_shell_constructs(cmds)
    logger.info(f"Output command count: {len(combined_cmds)}")

    # Debug the specific problem cases
    logger.info("=" * 70)
    logger.info("Testing processing in generate_entrypoint_with_structured_args:")

    # Process commands
    processed_commands = {}

    # Mock just the relevant part of generate_entrypoint_with_structured_args
    for cmd_type, cmds in service.run_cmd.items():
        logger.info(f"Processing command type: {cmd_type}")

        if isinstance(cmds, list):
            # Skip processing entirely empty lists
            if not cmds:
                logger.info("Skipping empty command list")
                processed_commands[cmd_type] = []
                continue

            # First combine any shell constructs that might be split across multiple elements
            # Filter out None and empty strings before combining
            valid_cmds = [c for c in cmds if c and isinstance(c, str) and c.strip()]
            if not valid_cmds:
                logger.info("No valid commands found in list")
                processed_commands[cmd_type] = []
                continue

            combined_cmds = env._combine_shell_constructs(valid_cmds)
            logger.info(
                f"Combined {len(valid_cmds)} commands into {len(combined_cmds)} constructs"
            )

            if not combined_cmds:
                logger.warning(
                    "Warning: _combine_shell_constructs returned an empty list!"
                )
                processed_commands[cmd_type] = []
                continue

            # Just check the results
            logger.info(f"Combined commands: {combined_cmds}")
            processed_commands[cmd_type] = combined_cmds

    logger.info("=" * 70)
    logger.info("Final results:")
    for cmd_type, processed_list in processed_commands.items():
        logger.info(f"Command type: {cmd_type}, Command count: {len(processed_list)}")


if __name__ in {"__main__", "__mp_main__"}:
    run_test()
