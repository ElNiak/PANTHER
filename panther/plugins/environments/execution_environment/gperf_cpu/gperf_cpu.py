import os
import time
from abc import ABC
from typing import Any

from omegaconf import OmegaConf
from panther.core.observer.management.event_manager import EventManager
from panther.config.config_experiment_schema import TestConfig
from panther.config.config_global_schema import GlobalConfig
from panther.plugins.environments.execution_environment.gperf_cpu.config_schema import (
    GperfCpuConfig,
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
    name="gperf_cpu",
    version="1.0.0",
    description="CPU profiling execution environment using Google Performance Tools",
    author="PANTHER Team",
    capabilities=["cpu_profiling", "performance_analysis", "hotspot_detection"],
    external_dependencies=["gperf"],
)
class GperfCpuEnvironment(IExecutionEnvironment, IOutputCollector, ABC):
    """
    GperfCpuEnvironment is a class that sets up and manages the execution environment
    for CPU profiling using gperf.

    Attributes:
        env_config_to_test (GperfCpuConfig): Configuration specific to the environment being tested.
        output_dir (str): Directory where output files will be stored.
        env_type (str): Type of the environment.
        env_sub_type (str): Sub-type of the environment.
        event_manager (EventManager): Manager for handling events.
        global_config (GlobalConfig): Global configuration settings.
        services_managers (list[IServiceManager]): List of service managers.
        test_config (TestConfig): Configuration for the test.
        plugin_loader (PluginLoader): Loader for plugins.
        logger (Logger): Logger for logging information.

    Methods:
        __init__(env_config_to_test, output_dir, env_type, env_sub_type, event_manager):
            Initializes the GperfCpuEnvironment with the given configuration and parameters.

        setup_environment(services_managers, test_config, global_config, timestamp, plugin_loader):
            Sets up the environment with the provided services managers, test configuration,
            global configuration, timestamp, and plugin loader.

        to_command(service_name):
            Generates the gperf command based on the configuration.

        __repr__():
            Returns a string representation of the GperfCpuEnvironment instance.
    """

    def __init__(
        self,
        env_config_to_test: GperfCpuConfig,
        output_dir: str,
        env_type: str,
        env_sub_type: str,
        event_manager: EventManager,
    ):
        super().__init__(env_config_to_test, output_dir, env_type, env_sub_type, event_manager)
        self.global_config = None
        self.env_config_to_test = env_config_to_test
        self.profile_files = []

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
            if service.service_config_to_test.implementation.gperf_compatible:
                service.environments["GPERF"] = True
                service.run_cmd["run_cmd"]["command_env"][
                    "LD_PRELOAD"
                ] = "/usr/local/lib/libprofiler.so"
                profile_file = f"/app/logs/{service.service_name}_cpu.prof"
                service.run_cmd["run_cmd"]["command_env"]["CPUPROFILE"] = profile_file
                # Track profile files for output collection
                self.profile_files.append(
                    {
                        "service": service.service_name,
                        "prof_file": profile_file,
                        "pdf_file": f"/app/logs/{service.service_name}_cpu.pdf",
                    }
                )
                # service.run_cmd["pre_run_cmds"] = service.run_cmd["pre_run_cmds"] + [self.to_command(service.service_name)]
                service.run_cmd["post_run_cmds"] = service.run_cmd["post_run_cmds"] + [
                    f"pprof --pdf /app/logs/{service.service_name}_cpu.prof > /app/logs/{service.service_name}_cpu.pdf"
                ]
                self.logger.debug("Service cmds: %s", service.run_cmd)
            else:
                self.logger.debug("Service %s is not gperf compatible", service)

        self.logger.debug("Test Config: %s", OmegaConf.to_yaml(self.test_config))
        self.logger.debug("Global Config: %s", OmegaConf.to_yaml(self.global_config))

    def to_command(self, service_name: str) -> str:
        """
        Generate the gperf command based on the configuration.
        """
        conf = GperfCpuConfig(
            # input_file="keywords.txt",
            # output_file="output.c",
            # language="C++",
            # keyword_only=True,
            # readonly_tables=True,
            # includes=["my_header.h"],
            # other_flags=["--ignore-case"]
        )
        command = ["gperf"]

        # Input and output files
        if conf.input_file:
            command.append(f'"{conf.input_file}"')
        if conf.output_file:
            command.append(f'--output-file="{conf.output_file}"')

        # Language option
        if conf.language:
            command.append(f"--language={conf.language}")

        # Flags
        if conf.keyword_only:
            command.append("--keyword-only")
        if conf.readonly_tables:
            command.append("--readonly-tables")
        if conf.switch:
            command.append("--switch")
        if conf.compare_strncmp:
            command.append("--compare-strncmp")

        # Custom functions
        if conf.hash_function:
            command.append(f'--hash-function="{conf.hash_function}"')
        if conf.compare_function:
            command.append(f'--compare-function="{conf.compare_function}"')

        # Includes
        for include in conf.includes:
            command.append(f'--include="{include}"')

        # Other flags
        command.extend(conf.other_flags)

        # Join and return the command
        return " ".join(command)

    def collect_outputs(self) -> dict[str, str]:
        """
        Collect CPU profiling outputs generated by gperf.

        Returns:
            dict[str, str]: Dictionary mapping output type to file path
        """
        outputs = {}

        for profile_info in self.profile_files:
            service_name = profile_info["service"]
            prof_file = profile_info["prof_file"]
            pdf_file = profile_info["pdf_file"]

            # Map container paths to host paths (assuming standard mapping)
            host_prof_file = prof_file.replace("/app/logs/", f"{self.output_dir}/")
            host_pdf_file = pdf_file.replace("/app/logs/", f"{self.output_dir}/")

            if os.path.exists(host_prof_file):
                outputs[f"cpu_profile_{service_name}"] = host_prof_file
                self.logger.debug(f"Collected CPU profile for {service_name}: {host_prof_file}")

            if os.path.exists(host_pdf_file):
                outputs[f"cpu_profile_pdf_{service_name}"] = host_pdf_file
                self.logger.debug(f"Collected CPU profile PDF for {service_name}: {host_pdf_file}")

        if not outputs:
            self.logger.warning("No gperf CPU profile outputs found")

        return outputs

    def get_output_metadata(self) -> dict[str, Any]:
        """
        Get metadata about the collected CPU profiling outputs.

        Returns:
            dict[str, Any]: Metadata including size, format, timestamp, etc.
        """
        metadata = {}

        for profile_info in self.profile_files:
            service_name = profile_info["service"]
            prof_file = profile_info["prof_file"]
            pdf_file = profile_info["pdf_file"]

            # Map container paths to host paths
            host_prof_file = prof_file.replace("/app/logs/", f"{self.output_dir}/")
            host_pdf_file = pdf_file.replace("/app/logs/", f"{self.output_dir}/")

            if os.path.exists(host_prof_file):
                stat_info = os.stat(host_prof_file)
                metadata[f"cpu_profile_{service_name}"] = {
                    "size_bytes": stat_info.st_size,
                    "format": "gperf_cpu_profile",
                    "timestamp": time.ctime(stat_info.st_mtime),
                    "path": host_prof_file,
                    "environment": "gperf_cpu",
                    "type": "cpu_profile",
                    "service": service_name,
                }

            if os.path.exists(host_pdf_file):
                stat_info = os.stat(host_pdf_file)
                metadata[f"cpu_profile_pdf_{service_name}"] = {
                    "size_bytes": stat_info.st_size,
                    "format": "pdf",
                    "timestamp": time.ctime(stat_info.st_mtime),
                    "path": host_pdf_file,
                    "environment": "gperf_cpu",
                    "type": "cpu_profile_visualization",
                    "service": service_name,
                }

        return metadata

    def __repr__(self):
        return (
            f"GperfEnvironment("
            f"env_config_to_test={self.env_config_to_test}, "
            f"output_dir={self.output_dir}, "
            f"event_manager={self.event_manager}, "
            f"services_managers={self.services_managers}, "
            f"test_config={self.test_config})"
        )
