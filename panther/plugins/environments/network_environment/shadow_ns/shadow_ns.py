import os
from pathlib import Path
import subprocess
import traceback
from typing import Any
import yaml
from panther.core.observer.event_manager import EventManager
from panther.config.config_experiment_schema import TestConfig
from panther.config.config_global_schema import GlobalConfig
from panther.plugins.services.services_interface import IServiceManager
from panther.plugins.environments.config_schema import EnvironmentConfig
from panther.plugins.environments.execution_environment.execution_environment_interface import (
    IExecutionEnvironment,
)
from panther.plugins.plugin_loader import PluginLoader
from panther.plugins.environments.network_environment.network_environment_interface import (
    INetworkEnvironment,
)
from panther.core.observer.event import Event


class ShadowNsEnvironment(INetworkEnvironment):
    """
    ShadowNsEnvironment is a class that manages the Shadow NS environment for testing purposes.
    It extends the INetworkEnvironment interface and provides methods to prepare, set up, deploy,
    monitor, and tear down the environment.

    - Real Applications:
      Shadow directly executes real, unmodified application binaries natively in Linux as standard OS
      processes and co-opts them into a discrete-event simulation.

    - Simulated Networks:
      Shadow intercepts and emulates system calls made by the co-opted processes, connecting them through
      an internal network using simulated implementations of common network protocols (e.g., TCP and UDP).
      (Reproducible experiments)

    - High Performance:
      Shadow focuses on high performance simulation, efficiently simulating both small client/server networks
      and large distributed systems. Shadow has been used to simulate real-world peer-to-peer networks such
      as Tor and Bitcoin.

    <!> Not all IUTs are compatible with Shadow (missing system calls, etc.)

    This network environment encapsulates the Shadow NS and all the services in a *single* Docker container.

    See: https://shadow.github.io/

    Attributes:
        docker_version (str): The version of the Docker image.
        docker_name (str): The name of the Docker container.
        services_network_config_file_path (Path): Path to the generated services network configuration file.
        rendered_services_network_config_file_path (Path): Path to the rendered services network configuration file.
        services_network_docker_file_path (Path): Path to the generated Dockerfile for services network.
        rendered_services_network_docker_file_path (Path): Path to the rendered Dockerfile for services network.

    Methods:
        __init__(self, env_config_to_test: EnvironmentConfig, output_dir: str, env_type: str, env_sub_type: str, event_manager: EventManager):
            Initializes the ShadowNsEnvironment with the given configuration.

        __str__(self):
            Returns a string representation of the ShadowNsEnvironment instance.

        __repr__(self):
            Returns a string representation of the ShadowNsEnvironment instance.

        prepare_environment(self):
            Prepares the service manager for use by building the Docker image.

        setup_environment(self, services_managers: List[IServiceManager], test_config: TestConfig, global_config: GlobalConfig, timestamp: str, plugin_loader: PluginLoader, execution_environment: List[IExecutionEnvironment]):

        deploy_services(self):
            Deploys the services in the Shadow NS environment.

        generate_environment_services(self, paths: Dict[str, str], timestamp: str):

        launch_environment_services(self):

        monitor_environment(self):

        teardown_environment(self):

        read_shadow_file(self) -> Dict[str, Any]:
            Reads the generated shadow.yml file and returns its contents as a dictionary.
    """

    def __init__(
        self,
        env_config_to_test: EnvironmentConfig,
        output_dir: str,
        env_type: str,
        env_sub_type: str,
        event_manager: EventManager,
    ):
        super().__init__(
            env_config_to_test, output_dir, env_type, env_sub_type, event_manager
        )

        self.docker_version = "v1"
        self.docker_name = "shadow_"

        self.services_network_config_file_path = Path(
            os.path.join(
                self._plugin_dir,
                env_type,
                env_sub_type,
                f"{env_sub_type}.generated.yml",
            )
        )
        self.rendered_services_network_config_file_path = Path(
            os.path.join(self.output_dir, f"{env_sub_type}.yml")
        )

        self.services_network_docker_file_path = Path(
            os.path.join(
                self._plugin_dir,
                env_type,
                env_sub_type,
                "Dockerfile.generated",
            )
        )
        self.rendered_services_network_docker_file_path = Path(
            os.path.join(self.output_dir, "Dockerfile.experience")
        )

    def __str__(self):
        return f"ShadowNsEnvironment({self.__dict__})"

    def __repr__(self):
        return f"ShadowNsEnvironment({self.__dict__})"

    def prepare_environment(self):
        """
        Prepare the service manager for use.
        """
        self.logger.info("Preparing Shadow NS service manager...")
        self.plugin_loader.build_docker_image_from_path(
            Path(
                os.path.join(
                    self._plugin_dir,
                    "network_environment",
                    "shadow_ns",
                    "Dockerfile",
                )
            ),
            "shadow_ns",
            self.docker_version,
        )

    def setup_environment(
        self,
        services_managers: list[IServiceManager],
        test_config: TestConfig,
        global_config: GlobalConfig,
        timestamp: str,
        plugin_loader: PluginLoader,
        execution_environment: list[IExecutionEnvironment],
    ):
        """
        Sets up the Shadow NS environment by generating the shadow.yml file with deployment commands.
        """
        self.update_environment(
            execution_environment,
            global_config,
            plugin_loader,
            services_managers,
            test_config,
        )
        self.prepare_environment()
        self.generate_environment_services(
            paths=self.global_config.paths, timestamp=timestamp
        )
        self.logger.info("Docker Compose environment setup complete")

    def deploy_services(self):
        self.logger.info("Deploying services")
        self.launch_environment_services()

    def generate_environment_services(self, paths: dict[str, str], timestamp: str):
        """
        Generates the shadow.yml file using the provided services and deployment commands.

        :param paths: Dictionary containing various path configurations.
        :param timestamp: The timestamp string to include in log paths.
        """
        # TODO add timeout in the test config
        # TODO check that the implementaion is compatible with shadow (in config file)
        # TODo moodify the shadow template to add the timeout also add folder for each service to be added in the multi stage
        try:
            # Ensure the log directory for each service exists
            for service in self.services_managers:
                assert (
                    service.service_config_to_test.implementation.shadow_compatible
                ), f"Service {service.service_name} is not compatible with Shadow NS. Please check the service configuration."
                self.create_log_dir(service)

                self.logger.debug(
                    f"Generating Docker Compose file for {service.service_name}"
                )

                self.docker_name = self.docker_name + service.service_name + "_"

                service.run_cmd["run_cmd"]["command_args"] = service.run_cmd["run_cmd"][
                    "command_args"
                ].replace("eth0", "lo")
                # TODO make this more general
                if service.role.name == "client":
                    service.run_cmd["run_cmd"]["command_args"] = service.run_cmd[
                        "run_cmd"
                    ]["command_args"].replace("$$TARGET_IP_HEX", "184549377")
                    service.run_cmd["run_cmd"]["command_args"] = service.run_cmd[
                        "run_cmd"
                    ]["command_args"].replace("$$IVY_IP_HEX", "184549378")
                else:
                    service.run_cmd["run_cmd"]["command_args"] = service.run_cmd[
                        "run_cmd"
                    ]["command_args"].replace("$$TARGET_IP_HEX", "184549378")
                    service.run_cmd["run_cmd"]["command_args"] = service.run_cmd[
                        "run_cmd"
                    ]["command_args"].replace("$$IVY_IP_HEX", "184549377")
                for other_service_name in self.services_managers:
                    if other_service_name.service_name != service.service_name:
                        # Shadow does not suport the _ in the service name -> replace by .
                        # TODO use "." in the service name for all plugins
                        if not "ivy" in service.service_name:
                            # TODO
                            service.run_cmd["run_cmd"]["command_args"] = service.run_cmd[
                                "run_cmd"
                            ]["command_args"].replace("_", ".")

            for service in self.services_managers:
                service.environments = self.resolve_environment_variables(
                    service.environments
                )
                service.environments["SHADOW_TEST"] = "1"
                self.logger.debug(
                    f"Service {service.service_name} environment: {service.environments}"
                )

            self.generate_from_template(
                "shadow-template.jinja",
                paths,
                timestamp,
                self.rendered_services_network_config_file_path,
                self.services_network_config_file_path,
            )

            self.logger.info(
                f"Shadow NS file generated at '{self.services_network_config_file_path}'"
            )

            self.logger.info("Shadow NS based environment manager prepared.")
            # Define docker container for experience
            self.generate_from_template(
                "Dockerfile.experience.jinja",
                paths,
                timestamp,
                self.rendered_services_network_docker_file_path,
                self.services_network_docker_file_path,
                str(self.services_network_config_file_path.name),
            )

            self.logger.info(
                f"Shadow NS file Dockerfile generated at '{self.services_network_docker_file_path}'"
            )

            self.get_docker_name()

        except Exception as e:
            self.logger.error(
                f"Failed to generate Shadow NS file: {e}\n{traceback.format_exc()}"
            )
            exit(1)

    def launch_environment_services(self):
        """
        Launches the Shadow NS environment using the generated shadow.yml file.
        """
        # TODO use docker_builder module
        try:
            with open(
                os.path.join(self.output_dir, "logs", "shadow.log"), "w"
            ) as log_file:
                with open(
                    os.path.join(self.output_dir, "logs", "shadow.err.log"), "w"
                ) as log_file_err:
                    volumes = [
                        "-v",
                        f"{os.path.abspath(self.log_dirs + '/shadow')}:/app/logs/",
                    ]
                    for service in self.services:
                        for volume in service.volumes:
                            volumes.append("-v")
                            if isinstance(volume, dict):
                                volumes.append(
                                    f"{os.path.abspath(volume['local'])}:{volume['container']}"
                                )
                            else:
                                volumes.append(f"{volume}")

                    command = [
                        "docker",
                        "run",
                        "--rm",
                        "-d",
                        "--sysctl",
                        "net.ipv6.conf.all.disable_ipv6=1",
                        "--security-opt",
                        "seccomp=unconfined",
                        "--shm-size=1024g",
                        "--privileged",
                        "--name",
                        self.docker_name,
                        *volumes,
                        self.docker_name,
                    ]
                    self.logger.debug(f"Executing command: {' '.join(command)}")
                    result = subprocess.run(
                        command,
                        check=True,
                        capture_output=True,
                        text=True,  # Ensures that output is in string format
                    )
                    # Write both stdout and stderr to the log file
                    log_file.write(result.stdout)
                    log_file_err.write(result.stderr)
                    # TODO shadow.data
                self.logger.info("Shadow NS environment launched successfully.")
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to launch Shadow NS environment: {e.stderr}")
            with open(
                os.path.join(self.output_dir, "logs", "shadow.log"), "w"
            ) as log_file:
                with open(
                    os.path.join(self.output_dir, "logs", "shadow.err.log"), "w"
                ) as log_file_err:
                    log_file.write(e.stdout)
                    log_file_err.write(e.stderr)

    def monitor_environment(self):
        """
        Monitors the Docker Compose environment by checking the status of services.
        """
        try:
            with open(
                os.path.join(self.output_dir, "logs", "docker-compose-ps.log"), "w"
            ) as log_file:
                with open(
                    os.path.join(self.output_dir, "logs", "docker-compose-ps.err.log"),
                    "w",
                ) as log_file_err:
                    result = subprocess.run(
                        [
                            "docker",
                            "ps",
                            "-f",
                            f"name={self.docker_name}",
                        ],
                        check=True,
                        capture_output=True,
                        text=True,  # Ensures that output is in string format
                    )
                    # Write both stdout and stderr to the log file
                    log_file.write(result.stdout)
                    log_file_err.write(result.stderr)
                    # NAME      IMAGE     COMMAND   SERVICE   CREATED   STATUS    PORTS
                    #
                    std_split = result.stdout.split("\n")
                    self.logger.debug(
                        f"docker-compose ps: {result.stdout} - {result.stderr} - {len(self.services_managers)}  - {len(std_split)}"
                    )
                    if len(std_split) < len(self.services_managers) + 1:
                        self.logger.debug(
                            "Docker Compose environment monitored successfully - Experiment finished earlier"
                        )
                        self.event_manager.notify(
                            Event(name="experiment_finished_early", data={})
                        )

                self.logger.debug("Docker Compose environment monitored successfully.")
        except subprocess.CalledProcessError as e:
            self.logger.error(
                f"Failed to monitor Docker Compose environment: {e.stderr}"
            )
            raise e

    def teardown_environment(self):
        """
        Tears down the Shadow NS environment by bringing down services.
        """
        # TODO: add a way to retrieve the logs, results, binary
        self.logger.info("Tearing down Shadow NS environment")
        with open(
            os.path.join(self.output_dir, "logs", "shadow-teardown.log"), "w"
        ) as log_file:
            with open(
                os.path.join(self.output_dir, "logs", "shadow-teardown.err.log"), "w"
            ) as log_file_err:
                try:
                    # Remove the docker image after execution
                    remove_image_command = [
                        "docker",
                        "rmi",
                        f"{self.docker_name}:latest",
                    ]
                    self.logger.debug(
                        f"Executing remove image command: {remove_image_command}"
                    )
                    result = subprocess.run(
                        remove_image_command,
                        check=True,
                        capture_output=True,
                        text=True,
                    )
                    self.logger.debug(f"Executing command: {remove_image_command}")

                    log_file.write(result.stdout)
                    log_file_err.write(result.stderr)
                    self.logger.info("Shadow NS environment torn down successfully")
                except subprocess.CalledProcessError as e:
                    self.logger.error(
                        f"Failed to tear down Shadow NS environment: {e.stderr}"
                    )
                    raise e

    def read_shadow_file(self) -> dict[str, Any]:
        """
        Reads the generated shadow.yml file.
        """
        if not os.path.exists(self.services_network_config_file_path):
            self.logger.error(
                f"Shadow NS file '{self.services_network_config_file_path}' does not exist."
            )
            raise FileNotFoundError(
                f"Shadow NS file '{self.services_network_config_file_path}' does not exist."
            )

        with open(self.services_network_config_file_path) as compose_file:
            return yaml.safe_load(compose_file)
