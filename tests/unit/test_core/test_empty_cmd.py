#!/usr/bin/env python3
"""
Test script to see how empty commands are handled in the _combine_shell_constructs method.
"""
import logging
import os

from panther.core.command_processor import ShellCommand
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
logger = logging.getLogger("test_empty_cmd")


class MockServiceManager:
    def __init__(self, service_name, commands):
        self.service_name = service_name
        self.run_cmd = commands
        self.volumes = []
        self.environments = {}
        self.service_config_to_test = type("obj", (object,), {"timeout": 60})

    def build_command_args(self, args):
        return args.split()


# Test cases for different command scenarios
def run_test():
    # Create temporary output directory
    output_dir = "/tmp/panther_test_empty"
    os.makedirs(output_dir, exist_ok=True)

    # Create event manager and config
    event_manager = EventManager()
    config = DockerComposeConfig()

    # Create the environment
    env = DockerComposeEnvironment(
        env_config_to_test=config,
        output_dir=output_dir,
        env_type="network_environment",
        env_sub_type="docker_compose",
        event_manager=event_manager,
    )

    # Test case 1: Empty command list
    cmds1 = []

    # Test case 2: A list with a valid shell construct
    cmds2 = [
        "while [ ! -f /app/sync_logs/ready.log ]; do",
        'echo "Waiting..." >> /app/logs/ready.log;',
        "sleep 2;",
        "done;",
    ]

    # Test case 3: A list with just None and empty values
    cmds3 = [None, "", None]

    # Test case 4: A list with empty strings mixed with valid commands
    cmds4 = ["", "echo 'Hello'", ""]

    # Test with different service managers
    service1 = MockServiceManager("service1", {"post_compile_cmds": cmds1})
    service2 = MockServiceManager("service2", {"post_compile_cmds": cmds2})
    service3 = MockServiceManager("service3", {"post_compile_cmds": cmds3})
    service4 = MockServiceManager("service4", {"post_compile_cmds": cmds4})

    # Set services on the environment
    env.services_managers = [service1, service2, service3, service4]

    # Test each service
    for i, service in enumerate([service1, service2, service3, service4], 1):
        logger.info(f"Testing service {i}: {service.service_name}")

        # Get the original commands
        original_cmds = service.run_cmd.get("post_compile_cmds", [])
        logger.info(f"Original commands: {original_cmds}")

        # Process with _combine_shell_constructs
        processed_cmds = env._combine_shell_constructs(original_cmds)
        logger.info(f"Processed commands: {processed_cmds}")

        # See how this would be handled in generate_entrypoint_with_structured_args
        processed_list = []
        for cmd in processed_cmds:
            if isinstance(cmd, str) and cmd.strip():
                shell_cmd = ShellCommand.from_string(cmd)
                processed_list.append(shell_cmd.to_dict())

        logger.info(f"Final processed list: {processed_list}")
        logger.info("-" * 50)


if __name__ in {"__main__", "__mp_main__"}:
    run_test()
