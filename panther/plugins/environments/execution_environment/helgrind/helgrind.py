from abc import ABC

from omegaconf import OmegaConf

from panther.core.observer.management.event_manager import EventManager
from panther.config.config_experiment_schema import TestConfig
from panther.config.config_global_schema import GlobalConfig
from panther.plugins.environments.execution_environment.helgrind.config_schema import (
    HelgrindConfig,
)
from panther.plugins.environments.execution_environment.execution_environment_interface import (
    IExecutionEnvironment,
)
from panther.plugins.plugin_loader import PluginLoader
from panther.plugins.services.services_interface import IServiceManager
from panther.plugins.plugin_decorators import register_plugin


@register_plugin(
    plugin_type="environment",
    name="helgrind",
    version="1.0.0",
    description="Thread error detection using Valgrind Helgrind",
    author="PANTHER Team",
    capabilities=[
        "race_detection",
        "deadlock_detection",
        "thread_safety",
        "synchronization_errors",
    ],
    external_dependencies=["valgrind>=3.15"],
)
class HelgrindEnvironment(IExecutionEnvironment, ABC):
    """
    HelgrindEnvironment is a class that sets up and manages the execution environment for Helgrind profiling.

    Attributes:
        global_config (GlobalConfig): The global configuration for the environment.
        env_config_to_test (HelgrindConfig): The specific configuration for the environment to test.
        services_managers (list[IServiceManager]): List of service managers.
        test_config (TestConfig): The test configuration.
        plugin_loader (PluginLoader): The plugin loader.
        logger (Logger): Logger for debugging and information.

    Methods:
        __init__(env_config_to_test: HelgrindConfig, output_dir: str, env_type: str, env_sub_type: str, event_manager: EventManager):
            Initializes the HelgrindEnvironment with the given configurations and event manager.

        setup_environment(services_managers: list[IServiceManager], test_config: TestConfig, global_config: GlobalConfig, timestamp: str, plugin_loader: PluginLoader):
            Sets up the environment with the provided service managers, test configuration, global configuration, timestamp, and plugin loader.

        to_command(service_name: str) -> str:
            Generates the gperf command based on the configuration.

        __repr__() -> str:
            Returns a string representation of the GperfHeapEnvironment instance.
    """

    def __init__(
        self,
        env_config_to_test: HelgrindConfig,
        output_dir: str,
        env_type: str,
        env_sub_type: str,
        event_manager: EventManager,
    ):
        super().__init__(env_config_to_test, output_dir, env_type, env_sub_type, event_manager)
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
        self.logger.debug("Services config: %s", self.env_config_to_test)
        for service in self.services_managers:
            self.logger.debug("Service cmds: %s", service.run_cmd)
            service_name = getattr(service, "service_name", service.__class__.__name__)

            # Emit environment modification started event
            if hasattr(self, "environment_emitter") and self.environment_emitter:
                self.environment_emitter.emit_environment_modification_started(
                    environment_id=f"helgrind_{service_name}",
                    environment_name="helgrind",
                    environment_type="execution",
                    target_service=service_name,
                    modification_type="command_wrapping",
                )

            # Store original command
            original_cmd = service.run_cmd["pre_run_cmds"].copy()
            service.run_cmd["pre_run_cmds"] = service.run_cmd["pre_run_cmds"] + [self.to_command()]

            # Emit environment modification completed event
            if hasattr(self, "environment_emitter") and self.environment_emitter:
                self.environment_emitter.emit_environment_modification_completed(
                    environment_id=f"helgrind_{service_name}",
                    environment_name="helgrind",
                    environment_type="execution",
                    modifications={
                        "pre_run_cmds": {
                            "original": original_cmd,
                            "modified": service.run_cmd["pre_run_cmds"],
                        }
                    },
                    modification_summary="Added valgrind helgrind command to pre_run_cmds",
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
        self.env_config_to_test = HelgrindConfig()
        command = [
            "valgrind",
            "--tool=helgrind",
            "--trace-children=yes",
            # "--show-reachable=yes",
            "--history-level=full",
            # "--log-file=" + str(self.output_dir) + "/helgrind.log",
        ]
        return " ".join(command)

    def __repr__(self):
        return (
            f"HelGrindEnvironment(env_config_to_test={self.env_config_to_test}, "
            f"output_dir={self.output_dir}, event_manager={self.event_manager}, "
            f"services_managers={self.services_managers}, test_config={self.test_config})"
        )
