from abc import ABC

from omegaconf import OmegaConf

from panther.core.observer.event_manager import EventManager
from panther.config.config_experiment_schema import TestConfig
from panther.config.config_global_schema import GlobalConfig
from panther.plugins.environments.execution_environment.strace.config_schema import (
    StraceConfig,
)
from panther.plugins.environments.execution_environment.execution_environment_interface import (
    IExecutionEnvironment,
)
from panther.plugins.plugin_loader import PluginLoader
from panther.plugins.services.services_interface import IServiceManager


class StraceEnvironment(IExecutionEnvironment, ABC):
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
        super().__init__(
            env_config_to_test, output_dir, env_type, env_sub_type, event_manager
        )
        self.global_config = None
        self.env_config_to_test = env_config_to_test

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
        self.logger.debug("Setup environment with:")
        self.logger.debug(f"Services config: {self.env_config_to_test}")
        for service in self.services_managers:
            self.logger.debug(f"Service cmds: {service.run_cmd}")
            service.run_cmd["pre_run_cmds"] = service.run_cmd["pre_run_cmds"] + [
                self.to_command()
            ]
            self.logger.debug(f"Service cmds: {service.run_cmd}")

        self.logger.debug(f"Test Config: {OmegaConf.to_yaml(self.test_config)}")
        self.logger.debug(f"Global Config: {OmegaConf.to_yaml(self.global_config)}")

    def to_command(self, pid: int | None = None) -> str:
        """
        Generate the strace command for execution.
        :param pid: Optional process ID to attach to.
        :return: Strace command as a string.
        """
        self.env_config_to_test = StraceConfig()
        excluded = ",".join(
            f"{syscall}" for syscall in self.env_config_to_test.excluded_syscalls
        )
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
        # command.append(f"-o {self.env_config_to_test.output_file}")
        return " ".join(command)

    def __repr__(self):
        return (
            f"StraceEnvironment(env_config_to_test={self.env_config_to_test}, "
            f"output_dir={self.output_dir}, event_manager={self.event_manager}, "
            f"services_managers={self.services_managers}, test_config={self.test_config})"
        )
