from omegaconf import OmegaConf

from panther.core.observer.management.event_manager import EventManager
from panther.config.config_experiment_schema import TestConfig
from typing import List

from panther.config.config_global_schema import GlobalConfig
from panther.plugins.environments.execution_environment.gperf_cpu.config_schema import (
    GperfCpuConfig,
)
from panther.plugins.environments.execution_environment.execution_environment_interface import (
    IExecutionEnvironment,
)
from panther.plugins.plugin_loader import PluginLoader
from panther.plugins.services.services_interface import IServiceManager

class GperfCommandBuilder:
    """Helper class to build gperf commands and reduce duplication."""
    
    @staticmethod
    def build_command(config: GperfCpuConfig) -> str:
        """Generate the gperf command based on the configuration."""
        command = ["gperf"]

        # Input and output files
        if config.input_file:
            command.append(f'"{config.input_file}"')
        if config.output_file:
            command.append(f'--output-file="{config.output_file}"')

        # Language option
        if config.language:
            command.append(f"--language={config.language}")

        # Flags
        if config.keyword_only:
            command.append("--keyword-only")
        if config.readonly_tables:
            command.append("--readonly-tables")
        if config.switch:
            command.append("--switch")
        if config.compare_strncmp:
            command.append("--compare-strncmp")

        # Custom functions
        if config.hash_function:
            command.append(f'--hash-function="{config.hash_function}"')
        if config.compare_function:
            command.append(f'--compare-function="{config.compare_function}"')

        # Includes
        for include in config.includes:
            command.append(f'--include="{include}"')

        # Other flags
        command.extend(config.other_flags)

        return " ".join(command)
    
    @staticmethod
    def configure_service_for_gperf(service: IServiceManager) -> None:
        """Configure a service manager for gperf profiling."""
        service.environments["GPERF"] = True
        service.run_cmd["run_cmd"]["command_env"]["LD_PRELOAD"] = "/usr/local/lib/libprofiler.so"
        service.run_cmd["run_cmd"]["command_env"]["CPUPROFILE"] = f"/app/logs/{service.service_name}_cpu.prof"
        service.run_cmd["post_run_cmds"] = service.run_cmd["post_run_cmds"] + [
            f"pprof --pdf /app/logs/{service.service_name}_cpu.prof > /app/logs/{service.service_name}_cpu.pdf"
        ]

class GperfCpuEnvironment(IExecutionEnvironment):
    def __init__(
        self,
        env_config_to_test: GperfCpuConfig,
        output_dir: str,
        env_type: str,
        env_sub_type: str,
        event_manager: EventManager):
        super().__init__(env_config_to_test, output_dir, env_type, env_sub_type, event_manager)
        self.env_config_to_test = env_config_to_test

    def setup_environment(
        self,
        services_managers: List[IServiceManager],
        test_config: TestConfig,
        global_config: GlobalConfig,
        timestamp: str,
        plugin_loader: PluginLoader):
        """
        Sets up the Docker Compose environment by generating the docker-compose.yml file with deployment commands.

        :param services: Dictionary of services with their configurations.
        :param deployment_info: Dictionary containing commands and volumes for each service.
        :param paths: Dictionary containing various path configurations.
        :param timestamp: The timestamp string to include in log paths.
        """
        self.services_managers: List[IServiceManager] = services_managers
        self.test_config = test_config
        self.plugin_loader = plugin_loader
        self.global_config = global_config
        self.logger.debug("Setup environment with:")
        self.logger.debug(f"Services config: {self.env_config_to_test}")
        
        for service in self.services_managers:
            self.logger.debug(f"Service cmds: {service.run_cmd}")
            if service.service_config_to_test.implementation.gperf_compatible:
                GperfCommandBuilder.configure_service_for_gperf(service)
                self.logger.debug(f"Service cmds after gperf config: {service.run_cmd}")
            else:
                self.logger.debug(f"Service {service} is not gperf compatible")

        # Convert Pydantic models to dict before using OmegaConf.to_yaml
        test_config_dict = self.test_config.dict() if hasattr(self.test_config, 'dict') else self.test_config
        global_config_dict = self.global_config.dict() if hasattr(self.global_config, 'dict') else self.global_config
        self.logger.debug(f"Test Config: {OmegaConf.to_yaml(test_config_dict)}")
        self.logger.debug(f"Global Config: {OmegaConf.to_yaml(global_config_dict)}")

    def to_command(self, service_name: str) -> str:
        """Generate the gperf command based on the configuration."""
        conf = GperfCpuConfig()  # Use default config for testing
        return GperfCommandBuilder.build_command(conf)

    def teardown_environment(self):
        raise NotImplementedError

    def __repr__(self):
        return (
            f"GperfEnvironment("
            f"env_config_to_test={self.env_config_to_test}, "
            f"output_dir={self.output_dir}, "
            f"event_manager={self.event_manager}, "
            f"services_managers={self.services_managers}, "
            f"test_config={self.test_config})"
        )
