import os
from pathlib import Path
import subprocess
import traceback
from panther.core.observer.event_manager import EventManager
from panther.config.config_experiment_schema import TestConfig
from panther.config.config_global_schema import GlobalConfig
from panther.plugins.environments.config_schema import EnvironmentConfig
from panther.plugins.services.services_interface import IServiceManager
from panther.plugins.environments.execution_environment.execution_environment_interface import (
    IExecutionEnvironment,
)
from panther.plugins.plugin_loader import PluginLoader
from panther.plugins.environments.network_environment.network_environment_interface import (
    INetworkEnvironment,
)
from panther.core.observer.event import Event


class LocalhostSingleContainerEnvironment(INetworkEnvironment):
    """
    LocalhostSingleContainerEnvironment is a class that manages a single container environment on localhost for testing purposes.
    It extends the INetworkEnvironment interface and provides methods to prepare, set up, deploy, monitor, and tear down the environment.

    Attributes:
        docker_version (str): The version of Docker to use.
        docker_name (str): The name prefix for the Docker container.
        services_network_config_file_path (Path): Path to the generated run.sh file.
        rendered_services_network_config_file_path (Path): Path to the rendered run.sh file.
        services_network_docker_file_path (Path): Path to the generated Dockerfile.
        rendered_services_network_docker_file_path (Path): Path to the rendered Dockerfile.

    Methods:
        __init__(env_config_to_test, output_dir, env_type, env_sub_type, event_manager):
            Initializes the LocalhostSingleContainerEnvironment with the given configuration.
        __str__():
            Returns a string representation of the LocalhostSingleContainerEnvironment instance.
        __repr__():
            Returns a string representation of the LocalhostSingleContainerEnvironment instance.
        prepare_environment():
            Prepares the service manager for use.
        setup_environment(services_managers, test_config, global_config, timestamp, plugin_loader, execution_environment):
        deploy_services():
            Deploys the services in the Localhost environment.
        generate_environment_services(paths, timestamp):
        launch_environment_services():
        monitor_environment():
        teardown_environment():
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
        self.docker_name = "localhost_"

        self.services_network_config_file_path = Path(
            os.path.join(
                self._plugin_dir,
                env_type,
                env_sub_type,
                "run.generated.sh",
            )
        )
        self.rendered_services_network_config_file_path = Path(
            os.path.join(self.output_dir, "run.sh")
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
        return f"LocalhostSingleContainerEnvironment({self.__dict__})"

    def __repr__(self):
        return f"LocalhostSingleContainerEnvironment({self.__dict__})"

    def prepare_environment(self):
        """
        Prepare the service manager for use.
        """
        self.logger.info("Preparing Localhost service manager...")
        # Additional setup can be implemented here
        self.plugin_loader.build_docker_image_from_path(
            Path(
                os.path.join(
                    self._plugin_dir.parent,
                    "services",
                    "Dockerfile",
                )
            ),
            "localhost_single_container",
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
        Sets up the Localhost environment by generating the run.sh file with deployment commands.
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
        self.logger.info("Localhost environment setup complete")

    def deploy_services(self):
        self.logger.info("Deploying services")
        self.launch_environment_services()

    def generate_environment_services(self, paths: dict[str, str], timestamp: str):
        """
        Generates the run.sh file using the provided services and deployment commands.

        :param paths: Dictionary containing various path configurations.
        :param timestamp: The timestamp string to include in log paths.
        """
        # TODO add timeout in the test config
        # TODO check that the implementaion is compatible with shadow (in config file)
        # TODo moodify the shadow template to add the timeout also add folder for each service to be added in the multi stage
        try:
            self.setup_execution_plugins(timestamp)
            # Ensure the log directory for each service exists
            for service in self.services_managers:
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
                    ]["command_args"].replace("$$TARGET_IP_HEX", "0x7f000001")
                    service.run_cmd["run_cmd"]["command_args"] = service.run_cmd[
                        "run_cmd"
                    ]["command_args"].replace("$$IVY_IP_HEX", "0x7f000001")
                else:
                    service.run_cmd["run_cmd"]["command_args"] = service.run_cmd[
                        "run_cmd"
                    ]["command_args"].replace("$$TARGET_IP_HEX", "0x7f000001")
                    service.run_cmd["run_cmd"]["command_args"] = service.run_cmd[
                        "run_cmd"
                    ]["command_args"].replace("$$IVY_IP_HEX", "0x7f000001")
                for other_service in self.services_managers:
                    if other_service.service_name != service.service_name:
                        # Shadow does not suport the _ in the service name -> replace by .
                        # TODO use "." in the service name for all plugins
                        service.run_cmd["run_cmd"]["command_args"] = (
                            service.run_cmd["run_cmd"]["command_args"]
                            .replace(other_service.service_name, "127.0.0.1")
                            .replace("eth0", "lo")
                        )
                        other_service.run_cmd["run_cmd"]["command_args"] = (
                            other_service.run_cmd["run_cmd"]["command_args"]
                            .replace(service.service_name, "127.0.0.1")
                            .replace("eth0", "lo")
                        )

            for service in self.services_managers:
                service.environments = self.resolve_environment_variables(
                    service.environments
                )
                self.logger.debug(
                    f"Service {service.service_name} environment: {service.environments}"
                )

            self.generate_from_template(
                "run.sh.jinja",
                paths,
                timestamp,
                self.rendered_services_network_config_file_path,
                self.services_network_config_file_path,
            )

            self.logger.info(
                f"Localhost file generated at '{self.services_network_config_file_path}'"
            )

            self.logger.info("Localhost based environment manager prepared.")
            self.generate_from_template(
                "Dockerfile.experience.jinja",
                paths,
                timestamp,
                self.rendered_services_network_docker_file_path,
                self.services_network_docker_file_path,
                self.services_network_config_file_path.name,
            )

            self.logger.info(
                f"Localhost file Dockerfile generated at '{self.services_network_docker_file_path}'"
            )

            self.get_docker_name()

        except Exception as e:
            self.logger.error(
                f"Failed to generate Localhost file: {e}\n{traceback.format_exc()}"
            )
            exit(1)

    def launch_environment_services(self):
        """
        Launches the Localhost environment using the generated run.sh file.
        """
        # TODO use docker_builder module
        try:
            with open(
                os.path.join(self.output_dir, "logs", "localhost.log"), "w"
            ) as log_file:
                with open(
                    os.path.join(self.output_dir, "logs", "localhost.err.log"), "w"
                ) as log_file_err:
                    volumes = [
                        "-v",
                        f"{os.path.abspath(self.log_dirs + '/localhost')}:/app/logs/",
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
                        "--privileged",
                        "--sysctl",
                        "net.ipv6.conf.all.disable_ipv6=1",
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
                self.logger.info("Localhost environment launched successfully.")
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to launch Localhost environment: {e.stderr}")
            with open(
                os.path.join(self.output_dir, "logs", "localhost.log"), "w"
            ) as log_file:
                with open(
                    os.path.join(self.output_dir, "logs", "localhost.err.log"), "w"
                ) as log_file_err:
                    log_file.write(e.stdout)
                    log_file_err.write(e.stderr)
            # raise e

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
        Tears down the Localhost environment by bringing down services.
        """
        # TODO: add a way to retrieve the logs, results, binary
        self.logger.info("Tearing down Localhost environment")
        with open(
            os.path.join(self.output_dir, "logs", "localhost-teardown.log"), "w"
        ) as log_file:
            with open(
                os.path.join(self.output_dir, "logs", "localhost-teardown.err.log"), "w"
            ) as log_file_err:
                try:
                    # Stop the running docker container
                    stop_container_command = ["docker", "stop", self.docker_name]
                    self.logger.debug(
                        f"Executing stop container command: {stop_container_command}"
                    )
                    result = subprocess.run(
                        stop_container_command,
                        check=True,
                        capture_output=True,
                        text=True,
                    )
                    log_file.write(result.stdout)
                    log_file_err.write(result.stderr)

                    # Remove the docker image after execution
                    remove_image_command = [
                        "docker",
                        "rm",
                        "--force",
                        f"{self.docker_name}",
                    ]
                    self.logger.debug(
                        f"Executing remove container command: {remove_image_command}"
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
                    
                    # Remove the docker image after execution
                    remove_image_command = [
                        "docker",
                        "rmi",
                        "--force",
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
                    self.logger.info("Localhost environment torn down successfully")
                except subprocess.CalledProcessError as e:
                    self.logger.error(
                        f"Failed to tear down Localhost environment: {e.stderr}"
                    )
                    with open(
                        os.path.join(self.output_dir, "logs", "localhost-teardown.log"),
                        "w",
                    ) as log_file:
                        with open(
                            os.path.join(
                                self.output_dir, "logs", "localhost-teardown.err.log"
                            ),
                            "w",
                        ) as log_file_err:
                            try:
                                stop_container_command = [
                                    "docker",
                                    "stop",
                                    self.docker_name,
                                ]
                                self.logger.debug(
                                    f"Executing stop container command: {stop_container_command}"
                                )
                                result = subprocess.run(
                                    stop_container_command,
                                    check=True,
                                    capture_output=True,
                                    text=True,
                                )
                                log_file.write(result.stdout)
                                log_file_err.write(result.stderr)
                                # Remove the docker image after execution
                                remove_image_command = [
                                    "docker",
                                    "rmi",
                                    "--force" f"{self.docker_name}:latest",
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
                                self.logger.debug(
                                    f"Executing command: {remove_image_command}"
                                )

                                log_file.write(result.stdout)
                                log_file_err.write(result.stderr)
                                self.logger.info(
                                    "Localhost environment torn down successfully"
                                )
                            except subprocess.CalledProcessError as e:
                                self.logger.error(
                                    f"Failed to tear down Localhost environment: {e.stderr}"
                                )
                                raise e
