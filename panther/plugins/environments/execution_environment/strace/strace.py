import os
import time
from abc import ABC
from typing import Any

from omegaconf import OmegaConf

from panther.core.observer.management.event_manager import EventManager
from panther.config.config_experiment_schema import TestConfig
from panther.config.config_global_schema import GlobalConfig
from panther.plugins.environments.execution_environment.strace.config_schema import (
    StraceConfig,
)
from panther.plugins.environments.execution_environment.execution_environment_interface import (
    IExecutionEnvironment,
)
from panther.plugins.environments.execution_environment.output_collector import IOutputCollector
from panther.plugins.plugin_loader import PluginLoader
from panther.plugins.services.services_interface import IServiceManager
from panther.plugins.plugin_decorators import register_plugin


@register_plugin(
    plugin_type="environment",
    name="strace",
    version="1.0.0",
    description="System call tracing execution environment",
    author="PANTHER Team",
    capabilities=["syscall_tracing", "performance_analysis", "debugging"],
    external_dependencies=["strace>=4.0"],
)
class StraceEnvironment(IExecutionEnvironment, IOutputCollector, ABC):
    """
    StraceEnvironment is a class that sets up and manages an execution environment using strace for system call tracing.

    Attributes:
        global_config (GlobalConfig): The global configuration for the environment.
        env_config_to_test (StraceConfig): The specific configuration for the strace environment to test.
        services_managers (list[IServiceManager]): List of service managers to handle services within the environment.
        test_config (TestConfig): Configuration for the test being executed.
        plugin_loader (PluginLoader): Loader for plugins used in the environment.

    Methods:
        __init__(env_config_to_test: StraceConfig, output_dir: str, env_type: str, env_sub_type: str, event_manager: EventManager):
            Initializes the StraceEnvironment with the given configuration and parameters.

        setup_environment(services_managers: list[IServiceManager], test_config: TestConfig, global_config: GlobalConfig, timestamp: str, plugin_loader: PluginLoader):
            Sets up the environment with the provided service managers, test configuration, global configuration, and plugin loader.

        to_command(pid: int | None = None) -> str:
            Generates the strace command for execution. Optionally attaches to a specific process ID.

        __repr__() -> str:
            Returns a string representation of the StraceEnvironment instance.
    """

    # TODO enforce config in environment
    def __init__(
        self,
        env_config_to_test: StraceConfig,
        output_dir: str,
        env_type: str,
        env_sub_type: str,
        event_manager: EventManager,
    ):
        super().__init__(env_config_to_test, output_dir, env_type, env_sub_type, event_manager)
        self.global_config = None
        self.env_config_to_test = env_config_to_test
        self.trace_output_file = None

    def setup_environment(
        self,
        services_managers: list[IServiceManager],
        test_config: TestConfig,
        global_config: GlobalConfig,
        timestamp: str,
        plugin_loader: PluginLoader,
    ):
        self.services_managers: list[IServiceManager] = services_managers
        self.test_config = test_config
        self.plugin_loader = plugin_loader
        self.global_config = global_config

        # Set up trace output file
        self.trace_output_file = os.path.join(self.output_dir, f"strace_{timestamp}.out")

        self.logger.debug("Setup environment with:")
        self.logger.debug("Services config: %s", self.env_config_to_test)
        for service in self.services_managers:
            self.logger.debug("Service cmds: %s", service.run_cmd)

            # Emit environment modification started event
            if hasattr(self, "environment_emitter") and self.environment_emitter:
                service_name = getattr(service, "service_name", service.__class__.__name__)
                self.environment_emitter.emit_environment_modification_started(
                    environment_id=f"strace_{service_name}",
                    environment_name="strace",
                    environment_type="execution",
                    target_service=service_name,
                    modification_type="command_wrapping",
                )

            # Modify the command
            original_cmd = service.run_cmd["pre_run_cmds"].copy()
            service.run_cmd["pre_run_cmds"] = service.run_cmd["pre_run_cmds"] + [self.to_command()]

            # Emit environment modification completed event
            if hasattr(self, "environment_emitter") and self.environment_emitter:
                self.environment_emitter.emit_environment_modification_completed(
                    environment_id=f"strace_{service_name}",
                    environment_name="strace",
                    environment_type="execution",
                    modifications={
                        "pre_run_cmds": {
                            "original": original_cmd,
                            "modified": service.run_cmd["pre_run_cmds"],
                        }
                    },
                    modification_summary="Added strace command to pre_run_cmds",
                )

            self.logger.debug("Service cmds: %s", service.run_cmd)

        self.logger.debug("Test Config: %s", OmegaConf.to_yaml(self.test_config))
        self.logger.debug("Global Config: %s", OmegaConf.to_yaml(self.global_config))

    def to_command(self, pid: int | None = None) -> str:
        """
        Generate the strace command for execution.
        :param pid: Optional process ID to attach to.
        :return: Strace command as a string.
        """
        self.env_config_to_test = StraceConfig()
        excluded = ",".join(f"{syscall}" for syscall in self.env_config_to_test.excluded_syscalls)
        command = [
            self.env_config_to_test.strace_binary,
            "-k",
        ]  # Include kernel stack if enabled
        command.append(f'-e trace="!{excluded}"')  # Exclude specified syscalls
        if pid:
            command.extend(["-p", str(pid)])
        # if self.env_config_to_test.trace_network_syscalls:
        #     command.append("-e trace=network")  # Include network-related syscalls
        # if self.env_config_to_test.additional_parameters:
        #     command.extend(self.env_config_to_test.additional_parameters)
        if self.trace_output_file:
            command.append(f"-o {self.trace_output_file}")
        return " ".join(command)

    def collect_outputs(self) -> dict[str, str]:
        """
        Collect trace outputs generated by strace.

        Returns:
            dict[str, str]: Dictionary mapping output type to file path
        """
        outputs = {}

        if self.trace_output_file and os.path.exists(self.trace_output_file):
            outputs["trace"] = self.trace_output_file
            self.logger.debug(f"Collected strace output: {self.trace_output_file}")
        else:
            self.logger.warning("No strace output file found")

        return outputs

    def get_output_metadata(self) -> dict[str, Any]:
        """
        Get metadata about the collected strace outputs.

        Returns:
            dict[str, Any]: Metadata including size, format, timestamp, etc.
        """
        metadata = {}

        if self.trace_output_file and os.path.exists(self.trace_output_file):
            stat_info = os.stat(self.trace_output_file)
            metadata["trace"] = {
                "size_bytes": stat_info.st_size,
                "format": "strace",
                "timestamp": time.ctime(stat_info.st_mtime),
                "path": self.trace_output_file,
                "environment": "strace",
                "type": "system_call_trace",
            }

        return metadata

    def __repr__(self):
        return (
            f"StraceEnvironment(env_config_to_test={self.env_config_to_test}, "
            f"output_dir={self.output_dir}, event_manager={self.event_manager}, "
            f"services_managers={self.services_managers}, test_config={self.test_config})"
        )
